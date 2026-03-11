"""Risk Prediction Dashboard Tab (Phase 2 — Step 2.5).

Adds a '📈 Risk Prediction' tab to the Gradio dashboard that:
1. Lets users input commit-level features (or auto-fill from last commit).
2. Runs the XGBoost model to predict conflict risk (0-100%).
3. Displays a risk gauge, SHAP factor table, and waterfall chart.
"""

import gradio as gr
from flagguard.core.logging import get_logger

logger = get_logger("ui.risk_dashboard")


def create_risk_prediction_tab():
    """Create the Risk Prediction Gradio tab component.

    Returns:
        Tab component reference.
    """
    with gr.TabItem("📈 Risk Prediction") as tab:
        gr.HTML(
            "<div style='padding:12px 16px;background:linear-gradient(135deg,"
            "rgba(234,179,8,0.15),rgba(239,68,68,0.1));"
            "border-radius:12px;border:1px solid rgba(234,179,8,0.2);"
            "margin-bottom:16px;'>"
            "<b style='color:#fbbf24;font-size:15px;'>📈 Predictive Risk Analysis</b>"
            "<br/><span style='color:#94a3b8;font-size:13px;'>"
            "XGBoost ML model predicts whether your commit will introduce flag conflicts. "
            "SHAP explains exactly which factors are driving the risk score."
            "</span></div>"
        )

        with gr.Row():
            # ── Left: Input Features ──
            with gr.Column(scale=1, elem_classes=["frosted-sidebar"]):
                gr.HTML("<div class='sidebar-title'>Commit Features</div>")

                files_modified = gr.Slider(
                    label="Files Modified", minimum=0, maximum=50, value=3, step=1
                )
                lines_added = gr.Slider(
                    label="Lines Added", minimum=0, maximum=1000, value=50, step=10
                )
                lines_deleted = gr.Slider(
                    label="Lines Deleted", minimum=0, maximum=500, value=20, step=5
                )
                flag_mentions = gr.Slider(
                    label="Flag Mentions (is_enabled, etc.)", minimum=0, maximum=20, value=0, step=1
                )

                gr.HTML("<div style='margin:8px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")

                py_files = gr.Slider(label="Python Files", minimum=0, maximum=20, value=1, step=1)
                js_files = gr.Slider(label="JS/TS Files", minimum=0, maximum=20, value=0, step=1)
                config_files = gr.Slider(label="Config Files (.json/.yaml)", minimum=0, maximum=10, value=0, step=1)

                gr.HTML("<div style='margin:8px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")

                commit_hour = gr.Slider(label="Commit Hour (0-23)", minimum=0, maximum=23, value=14, step=1)
                is_merge = gr.Checkbox(label="Merge Commit", value=False)
                msg_length = gr.Slider(label="Message Length (chars)", minimum=1, maximum=200, value=50, step=5)
                has_tests = gr.Checkbox(label="Includes Test Changes", value=True)
                author_commits = gr.Slider(label="Author Total Commits", minimum=1, maximum=300, value=30, step=5)
                days_since = gr.Slider(label="Days Since Last Commit", minimum=0.0, maximum=30.0, value=1.0, step=0.5)
                diff_ratio = gr.Slider(label="Delete/Add Ratio", minimum=0.0, maximum=5.0, value=0.4, step=0.1)

                predict_btn = gr.Button("🔮 Predict Risk", elem_classes=["glass-btn"])

            # ── Right: Results ──
            with gr.Column(scale=3):
                with gr.Tabs():
                    with gr.TabItem("🎯 Risk Score"):
                        risk_gauge_html = gr.HTML(
                            _render_gauge(0.0, "unknown")
                        )
                        risk_summary = gr.Markdown(
                            "*Configure commit features and click 'Predict Risk' to see the ML prediction.*"
                        )

                    with gr.TabItem("🔬 SHAP Factors"):
                        shap_table = gr.Markdown(
                            "*SHAP feature attributions will be shown here after prediction.*"
                        )

                    with gr.TabItem("📊 Feature Importance"):
                        importance_chart = gr.Markdown(
                            "*Top contributing features with direction and magnitude.*"
                        )

        # ── Event Handler ──
        def run_prediction(
            f_mod, l_add, l_del, flags, py_f, js_f, conf_f,
            c_hour, merge, msg_len, tests, auth_cnt, d_since, d_ratio,
        ):
            """Run the XGBoost prediction and format results."""
            try:
                from flagguard.ai.risk_explainer import RiskExplainer

                explainer = RiskExplainer()

                if not explainer.is_available:
                    return (
                        _render_gauge(0.0, "unavailable"),
                        "⚠️ **Model not loaded.** Train it first:\n```bash\npython scripts/generate_training_data.py\npython notebooks/train_risk_model.py\n```",
                        "*Model not available.*",
                        "*Model not available.*",
                    )

                features = {
                    "files_modified": f_mod,
                    "lines_added": l_add,
                    "lines_deleted": l_del,
                    "flag_mentions_count": flags,
                    "py_files_modified": py_f,
                    "js_files_modified": js_f,
                    "config_files_modified": conf_f,
                    "commit_hour": c_hour,
                    "is_merge_commit": int(merge),
                    "message_length": msg_len,
                    "has_test_changes": int(tests),
                    "author_commit_count": auth_cnt,
                    "days_since_last_commit": d_since,
                    "diff_size_ratio": d_ratio,
                }

                result = explainer.predict_and_explain(features)

                # Risk gauge
                gauge = _render_gauge(result.risk_score, result.risk_level)

                # Summary
                icon = {"low": "✅", "medium": "⚠️", "high": "🔶", "critical": "🔴"}.get(
                    result.risk_level, "❓"
                )
                summary = (
                    f"### {icon} Risk Level: **{result.risk_level.upper()}** "
                    f"({result.risk_score * 100:.1f}%)\n\n"
                )

                if result.prediction == 1:
                    summary += (
                        "This commit profile has characteristics that **correlate with flag conflicts**. "
                        "Review the SHAP factors tab to understand which features are driving this score."
                    )
                else:
                    summary += (
                        "This commit profile appears **safe** based on historical patterns. "
                        "The model doesn't predict flag conflicts for this combination of features."
                    )

                # SHAP factors table
                if result.top_factors:
                    shap_md = "### Top Contributing Factors (SHAP)\n\n"
                    shap_md += "| Rank | Feature | Value | Impact | Direction |\n"
                    shap_md += "|------|---------|-------|--------|-----------|\n"
                    for i, factor in enumerate(result.top_factors, 1):
                        bar = "🟥" if factor["impact"] > 0 else "🟩"
                        shap_md += (
                            f"| {i} | `{factor['feature']}` | {factor['value']} | "
                            f"{bar} {abs(factor['impact']):.4f} | {factor['direction']} |\n"
                        )
                else:
                    shap_md = "*No SHAP data available.*"

                # Feature importance chart (text-based bar chart)
                if result.top_factors:
                    chart_md = "### Feature Impact Visualization\n\n```\n"
                    max_impact = max(abs(f["impact"]) for f in result.top_factors) or 1
                    for factor in result.top_factors:
                        bar_len = int(abs(factor["impact"]) / max_impact * 30)
                        if factor["impact"] > 0:
                            bar = "🔴" + "█" * bar_len
                            label = "↑ RISK"
                        else:
                            bar = "🟢" + "█" * bar_len
                            label = "↓ SAFE"
                        chart_md += f"  {factor['feature']:30s} {bar} {label}\n"
                    chart_md += "```"
                else:
                    chart_md = "*No importance data.*"

                return gauge, summary, shap_md, chart_md

            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                return (
                    _render_gauge(0.0, "error"),
                    f"❌ **Error:** {e}",
                    "*Prediction failed.*",
                    "*Prediction failed.*",
                )

        predict_btn.click(
            fn=run_prediction,
            inputs=[
                files_modified, lines_added, lines_deleted, flag_mentions,
                py_files, js_files, config_files,
                commit_hour, is_merge, msg_length, has_tests,
                author_commits, days_since, diff_ratio,
            ],
            outputs=[risk_gauge_html, risk_summary, shap_table, importance_chart],
        )

    return tab


def _render_gauge(score: float, level: str) -> str:
    """Render a CSS-based risk gauge as HTML."""
    pct = int(score * 100)

    colors = {
        "low": "#22c55e",
        "medium": "#f59e0b",
        "high": "#f97316",
        "critical": "#ef4444",
        "unknown": "#64748b",
        "unavailable": "#64748b",
        "error": "#ef4444",
    }
    color = colors.get(level, "#64748b")

    return f"""
    <div style="text-align:center;padding:32px 0;">
        <div style="position:relative;width:200px;height:200px;margin:0 auto;">
            <svg viewBox="0 0 200 200" style="transform:rotate(-90deg);">
                <circle cx="100" cy="100" r="85" fill="none"
                    stroke="rgba(255,255,255,0.05)" stroke-width="12"/>
                <circle cx="100" cy="100" r="85" fill="none"
                    stroke="{color}" stroke-width="12"
                    stroke-dasharray="{pct * 5.34} 534"
                    stroke-linecap="round"
                    style="transition:stroke-dasharray 0.8s ease;"/>
            </svg>
            <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                text-align:center;">
                <div style="font-size:42px;font-weight:bold;color:{color};">{pct}%</div>
                <div style="font-size:14px;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:2px;margin-top:4px;">{level}</div>
            </div>
        </div>
        <div style="color:#64748b;margin-top:12px;font-size:13px;">
            Conflict Risk Score (XGBoost + SHAP)
        </div>
    </div>
    """
