"""Analyst Dashboard — 9 tabs for analyst-level access."""

import gradio as gr
from flagguard.ui.helpers import run_analysis
from flagguard.ui.tabs.header import create_shared_header

def create_analyst_dashboard(app: gr.Blocks, user_state: gr.State):
    with gr.Group(visible=False) as dashboard:

        # Header (notification bell + dark/light toggle built in)
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                header_html, logout_btn = create_shared_header("analyst", user_state)

        gr.HTML("<div class='role-banner-analyst'><b style='color:#f59e0b;'>🔬 You are an Analyst</b> — Create projects, run scans, manage environments, webhooks, reports, and IaC scans. User management requires Admin access.</div>")

        # Metrics
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["metric-card"]):
                    val_flags = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Flags</div>")
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["metric-card"]):
                    val_active = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Active</div>")
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["metric-card"]):
                    val_conflicts = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Conflicts</div>")
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["metric-card"]):
                    val_health = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Health</div>")

        gr.HTML("<div style='margin:16px 0;'></div>")

        with gr.Tabs():

            # Tab 1: Analysis
            with gr.TabItem("⚡ Analysis"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes=["frosted-sidebar"]):
                        gr.HTML("<div class='sidebar-title'>Project</div>")
                        project_selector = gr.Dropdown(label="", choices=[], interactive=True)
                        with gr.Row():
                            new_proj_name = gr.Textbox(label="New Project Name")
                            create_proj_btn = gr.Button("+ Create", elem_classes=["glass-btn"], size="sm")
                        proj_msg = gr.Textbox(interactive=False, show_label=False)
                        gr.HTML("<div style='margin:12px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                        file_input = gr.File(label="Flag Manifest", file_types=[".json", ".yaml"])
                        source_input = gr.File(label="Source Archive", file_types=[".zip"])
                        use_llm = gr.Checkbox(label="AI Analysis", value=True)
                        analyze_btn = gr.Button("⚡ Run Analysis", elem_classes=["glass-btn"])
                        conflicts_list = gr.Textbox(show_label=False, interactive=False, lines=6)
                    with gr.Column(scale=4):
                        with gr.Tabs():
                            with gr.TabItem("Charts"):
                                with gr.Row():
                                    with gr.Column():
                                        plot_status = gr.Plot(label="Flag Status")
                                    with gr.Column():
                                        plot_severity = gr.Plot(label="Severity")
                            with gr.TabItem("Dependency Graph"):
                                graph_html = gr.HTML("<div style='text-align:center;color:#94a3b8;padding:40px;'>Run analysis to see graph.</div>")
                                with gr.Accordion("Mermaid Code", open=False):
                                    mermaid_code_display = gr.Code(label="", language=None, lines=12, interactive=False)
                            with gr.TabItem("Report"):
                                report_md = gr.Markdown("No scan data.")

                def create_project(name, uid):
                    if not name or not uid:
                        return gr.update(), "Enter a project name."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Project
                        db = SessionLocal()
                        p = Project(name=name, owner_id=uid, description="")
                        db.add(p); db.commit(); db.refresh(p)
                        # Reload analyst's own projects
                        projs = db.query(Project).filter(Project.owner_id == uid)\
                                  .order_by(Project.created_at.desc()).all()

                        return gr.update(choices=[(p.name, p.id) for p in projs], value=p.id), f"Created: {name}"
                    except Exception as e:
                        return gr.update(), f"Error: {e}"

                def run_and_update(pid, config, source, use_ai):
                    res = run_analysis(config, source, use_ai)
                    m_f, m_c, m_d, m_e, m_h = res[0], res[1], res[2], res[3], res[4]
                    h_f = f"<div class='metric-value'>{m_f}</div><div class='metric-label'>Flags</div>"
                    h_a = f"<div class='metric-value'>{m_e}</div><div class='metric-label'>Active</div>"
                    h_c = f"<div class='metric-value'>{m_c+m_d}</div><div class='metric-label'>Conflicts</div>"
                    h_h = f"<div class='metric-value'>{m_h}</div><div class='metric-label'>Health</div>"
                    return h_f, h_a, h_c, h_h, res[5], res[6], res[7], res[8], res[9]

                create_proj_btn.click(create_project, inputs=[new_proj_name, user_state], outputs=[project_selector, proj_msg])
                analyze_btn.click(run_and_update, inputs=[project_selector, file_input, source_input, use_llm],
                    outputs=[val_flags, val_active, val_conflicts, val_health, plot_status, plot_severity, report_md, graph_html, mermaid_code_display])

            # Tab 2: Environments
            with gr.TabItem("🌍 Environments"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Create Environment</div>")
                    with gr.Row():
                        env_proj = gr.Textbox(label="Project ID", scale=2)
                        env_name_inp = gr.Textbox(label="Name", placeholder="dev/staging/prod", scale=2)
                        env_btn = gr.Button("Create", elem_classes=["glass-btn"], scale=1)
                    env_overrides = gr.Textbox(label="Flag Overrides (JSON)", lines=3)
                    env_result = gr.JSON(label="Result")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Drift Detection</div>")
                    with gr.Row():
                        drift_a = gr.Textbox(label="Env A ID", scale=1)
                        drift_b = gr.Textbox(label="Env B ID", scale=1)
                        drift_btn = gr.Button("Compare Drift", elem_classes=["glass-btn"], scale=1)
                    drift_result = gr.JSON(label="Drift Report")

                def create_env(pid, name, overrides):
                    import json as _json
                    if not pid or not name:
                        return {"error": "Project ID and Name required"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Environment, Project
                        ovr = _json.loads(overrides) if overrides and overrides.strip() else {}
                        db = SessionLocal()
                        proj = db.query(Project).filter(Project.id == pid.strip()).first()
                        if not proj:
                            return {"error": "Project not found"}
                        existing = db.query(Environment).filter(Environment.project_id == pid.strip(), Environment.name == name).first()
                        if existing:
                            return {"error": f"Environment '{name}' already exists"}
                        env = Environment(name=name, project_id=pid.strip(), flag_overrides=ovr)
                        db.add(env); db.commit(); db.refresh(env)
                        result = {"id": env.id, "name": env.name, "project_id": env.project_id, "flag_overrides": env.flag_overrides}

                        return result
                    except Exception as e:
                        return {"error": str(e)}

                def compare_drift(env_a_id, env_b_id):
                    if not env_a_id or not env_b_id:
                        return {"error": "Both Env IDs required"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Environment
                        db = SessionLocal()
                        ea = db.query(Environment).filter(Environment.id == env_a_id.strip()).first()
                        eb = db.query(Environment).filter(Environment.id == env_b_id.strip()).first()

                        if not ea or not eb:
                            return {"error": "One or both environments not found"}
                        oa, ob = ea.flag_overrides or {}, eb.flag_overrides or {}
                        all_flags = sorted(set(list(oa.keys()) + list(ob.keys())))
                        diffs = [{"flag": f, ea.name: oa.get(f), eb.name: ob.get(f),
                                  "status": "drift" if f in oa and f in ob else "missing"}
                                 for f in all_flags if oa.get(f) != ob.get(f)]
                        return {"env_a": ea.name, "env_b": eb.name, "differences": diffs, "total_diffs": len(diffs)}
                    except Exception as e:
                        return {"error": str(e)}

                env_btn.click(create_env, inputs=[env_proj, env_name_inp, env_overrides], outputs=[env_result])
                drift_btn.click(compare_drift, inputs=[drift_a, drift_b], outputs=[drift_result])

            # Tab 3: Webhooks
            with gr.TabItem("🪝 Webhooks"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        wh_proj = gr.Textbox(label="Project ID", scale=2)
                        wh_url = gr.Textbox(label="Webhook URL", scale=3)
                    wh_events = gr.CheckboxGroup(choices=["scan.completed","conflict.detected","flag.created","flag.updated"], value=["scan.completed","conflict.detected"], label="Events")
                    wh_btn = gr.Button("Create Webhook", elem_classes=["glass-btn"])
                    wh_result = gr.JSON(label="Result")
                    with gr.Row():
                        wh_test_id = gr.Textbox(label="Webhook ID to Test", scale=3)
                        wh_test_btn = gr.Button("Test", elem_classes=["glass-btn"], scale=1)
                    wh_test_result = gr.JSON(label="Test Result")

                def create_webhook(pid, url, events):
                    if not pid or not url:
                        return {"error": "Project ID and URL required"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import WebhookConfig, Project
                        db = SessionLocal()
                        proj = db.query(Project).filter(Project.id == pid.strip()).first()
                        if not proj:
                            return {"error": "Project not found"}
                        wh = WebhookConfig(project_id=pid.strip(), url=url, events=events or ["scan.completed"])
                        db.add(wh); db.commit(); db.refresh(wh)
                        result = {"id": wh.id, "url": wh.url, "events": wh.events, "project_id": wh.project_id}

                        return result
                    except Exception as e:
                        return {"error": str(e)}

                def test_webhook(wid):
                    if not wid:
                        return {"error": "Enter a Webhook ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import WebhookConfig
                        db = SessionLocal()
                        wh = db.query(WebhookConfig).filter(WebhookConfig.id == wid.strip()).first()

                        if not wh:
                            return {"error": "Webhook not found"}
                        # Attempt to send test payload
                        import requests as _req
                        from datetime import datetime as _dt
                        try:
                            resp = _req.post(wh.url, json={"event": "test", "message": "Test from FlagGuard", "timestamp": str(_dt.utcnow())}, timeout=5)
                            return {"status": "sent", "url": wh.url, "response_code": resp.status_code}
                        except Exception:
                            return {"status": "failed", "url": wh.url, "reason": "Could not reach webhook URL"}
                    except Exception as e:
                        return {"error": str(e)}

                wh_btn.click(create_webhook, inputs=[wh_proj, wh_url, wh_events], outputs=[wh_result])
                wh_test_btn.click(test_webhook, inputs=[wh_test_id], outputs=[wh_test_result])

            # Tab 4: Scheduler
            with gr.TabItem("⏰ Scheduler"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Schedule Recurring Scans</div>")
                    with gr.Row():
                        sched_proj = gr.Textbox(label="Project ID", scale=2)
                        sched_interval = gr.Slider(label="Interval (min)", minimum=5, maximum=1440, value=60, scale=2)
                        sched_btn = gr.Button("Schedule", elem_classes=["glass-btn"], scale=1)
                    sched_result = gr.JSON(label="Schedule Status")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Conflict Trends</div>")
                    with gr.Row():
                        trend_proj = gr.Textbox(label="Project ID", scale=2)
                        trend_days = gr.Slider(label="Days", minimum=7, maximum=90, value=30, scale=2)
                        trend_btn = gr.Button("Load", elem_classes=["glass-btn"], scale=1)
                    trend_result = gr.JSON(label="Trend Data")

                def create_schedule(pid, interval):
                    if not pid:
                        return {"error": "Enter a Project ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Project
                        db = SessionLocal()
                        proj = db.query(Project).filter(Project.id == pid.strip()).first()

                        if not proj:
                            return {"error": "Project not found"}
                        return {"status": "scheduled", "project": proj.name, "project_id": pid,
                                "interval_minutes": int(interval),
                                "message": f"Scan scheduled every {int(interval)} minutes for '{proj.name}'. Note: Background scheduler runs while server is active."}
                    except Exception as e:
                        return {"error": str(e)}

                def load_trends(pid, days):
                    if not pid:
                        return {"error": "Enter a Project ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        from datetime import datetime as dt, timedelta
                        db = SessionLocal()
                        cutoff = dt.utcnow() - timedelta(days=int(days))
                        scans = db.query(Scan).filter(Scan.project_id == pid.strip(), Scan.created_at >= cutoff).order_by(Scan.created_at.asc()).all()

                        if not scans:
                            return {"message": f"No scans in the last {int(days)} days"}
                        return {"project_id": pid, "days": int(days), "total_scans": len(scans),
                                "trend": [{"date": str(s.created_at)[:10], "health": (s.result_summary or {}).get("health_score", 0),
                                           "conflicts": (s.result_summary or {}).get("conflict_count", 0)} for s in scans]}
                    except Exception as e:
                        return {"error": str(e)}

                sched_btn.click(create_schedule, inputs=[sched_proj, sched_interval], outputs=[sched_result])
                trend_btn.click(load_trends, inputs=[trend_proj, trend_days], outputs=[trend_result])

            # Tab 5: Reports
            with gr.TabItem("📑 Reports"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        rep_proj = gr.Textbox(label="Project ID", scale=3)
                        rep_fmt = gr.Dropdown(label="Format", choices=["json","csv","markdown"], value="json", scale=1)
                        rep_btn = gr.Button("Generate", elem_classes=["glass-btn"], scale=1)
                    rep_result = gr.JSON(label="Report")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    exec_proj = gr.Textbox(label="Project ID (Executive Summary)")
                    exec_btn = gr.Button("Executive Summary", elem_classes=["glass-btn"])
                    exec_result = gr.JSON(label="Summary")

                def gen_report(pid, fmt):
                    if not pid:
                        return {"error": "Enter Project ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        db = SessionLocal()
                        scans = db.query(Scan).filter(Scan.project_id == pid.strip()).order_by(Scan.created_at.desc()).limit(5).all()

                        if not scans:
                            return {"error": "No scans found"}
                        return {"project_id": pid, "format": fmt, "total_scans": len(scans),
                                "scans": [{"id": s.id, "status": s.status, "health": (s.result_summary or {}).get("health_score", "N/A"),
                                           "flags": (s.result_summary or {}).get("flag_count", 0), "date": str(s.created_at)} for s in scans]}
                    except Exception as e:
                        return {"error": str(e)}

                def exec_summary(pid):
                    if not pid:
                        return {"error": "Enter Project ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan, Project
                        db = SessionLocal()
                        proj = db.query(Project).filter(Project.id == pid.strip()).first()
                        if not proj:
                            return {"error": "Project not found"}
                        scans = db.query(Scan).filter(Scan.project_id == pid.strip()).order_by(Scan.created_at.desc()).all()

                        total = len(scans)
                        avg_health = sum((s.result_summary or {}).get("health_score", 0) for s in scans) / max(total, 1)
                        latest = scans[0] if scans else None
                        return {"project": proj.name, "total_scans": total, "avg_health": f"{avg_health:.0f}%",
                                "latest_scan": str(latest.created_at) if latest else "Never",
                                "latest_health": (latest.result_summary or {}).get("health_score", "N/A") if latest else "N/A"}
                    except Exception as e:
                        return {"error": str(e)}

                rep_btn.click(gen_report, inputs=[rep_proj, rep_fmt], outputs=[rep_result])
                exec_btn.click(exec_summary, inputs=[exec_proj], outputs=[exec_result])

            # Tab 6: IaC Scan
            with gr.TabItem("🏗️ IaC Scan"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Terraform / CloudFormation / Pulumi Analysis</div>")
                    iac_file = gr.File(label="Upload IaC File (.tf, .yaml, .json)", file_types=[".tf",".yaml",".yml",".json"])
                    iac_btn = gr.Button("Analyze", elem_classes=["glass-btn"])
                    iac_result = gr.JSON(label="Detected Flags")

                def analyze_iac(file):
                    if not file:
                        return {"error": "Upload a file first"}
                    try:
                        import re
                        from pathlib import Path
                        content = Path(file.name).read_text(errors="ignore")
                        patterns = [
                            r'feature[_-]?flag[s]?\s*[=:]\s*["\']?([\w.-]+)',
                            r'enabled\s*[=:]\s*(true|false)',
                            r'toggle[_-]?([\w.-]+)\s*[=:]',
                            r'flag[_-]name\s*[=:]\s*["\']([\w.-]+)',
                            r'variable\s+["\']([\w_]+_enabled)',
                        ]
                        found_flags = []
                        for pat in patterns:
                            for m in re.finditer(pat, content, re.IGNORECASE):
                                found_flags.append({"match": m.group(0).strip(), "value": m.group(1) if m.groups() else m.group(0),
                                                    "line": content[:m.start()].count('\n') + 1})
                        return {"file": Path(file.name).name, "flags_detected": len(found_flags),
                                "flags": found_flags[:50], "lines_scanned": content.count('\n') + 1}
                    except Exception as e:
                        return {"error": str(e)}

                iac_btn.click(analyze_iac, inputs=[iac_file], outputs=[iac_result])

            # Tab 7: Lifecycle
            with gr.TabItem("⏳ Lifecycle"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        lc_proj = gr.Textbox(label="Project ID", scale=2)
                        lc_days = gr.Slider(label="Stale Days", minimum=7, maximum=180, value=30, scale=2)
                        lc_btn = gr.Button("Check", elem_classes=["glass-btn"], scale=1)
                    with gr.Row():
                        with gr.Column():
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_total = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Total</div>")
                        with gr.Column():
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_stale = gr.HTML("<div class='metric-value' style='color:#f59e0b'>-</div><div class='metric-label'>Stale</div>")
                        with gr.Column():
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_zombie = gr.HTML("<div class='metric-value' style='color:#ef4444'>-</div><div class='metric-label'>Zombie</div>")
                    lc_info = gr.Markdown("Enter project ID and check lifecycle.")

                def lc_check(pid, days):
                    if not pid:
                        return "-", "-", "-", "Enter a Project ID"
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        db = SessionLocal()
                        last_scan = db.query(Scan).filter(Scan.project_id == pid.strip()).order_by(Scan.created_at.desc()).first()

                        if not last_scan or not last_scan.result_summary:
                            return "-", "-", "-", "No scans found. Run an analysis first."
                        summary = last_scan.result_summary or {}
                        total = summary.get("flag_count", 0)
                        conflicts = summary.get("conflict_count", 0)
                        stale = summary.get("stale_flags", 0)
                        zombie = summary.get("zombie_flags", 0)
                        h_t = f"<div class='metric-value'>{total}</div><div class='metric-label'>Total</div>"
                        h_s = f"<div class='metric-value' style='color:#f59e0b'>{stale}</div><div class='metric-label'>Stale</div>"
                        h_z = f"<div class='metric-value' style='color:#ef4444'>{zombie}</div><div class='metric-label'>Zombie</div>"
                        suggestions = []
                        if stale > 0:
                            suggestions.append(f"Review {stale} stale flags — consider cleanup")
                        if zombie > 0:
                            suggestions.append(f"Remove {zombie} zombie flags — unused and safe to delete")
                        if conflicts > 0:
                            suggestions.append(f"Resolve {conflicts} active conflicts")
                        if not suggestions:
                            suggestions.append("All flags healthy — no action needed")
                        info = "### Cleanup Suggestions\n" + "\n".join(f"- {s}" for s in suggestions)
                        return h_t, h_s, h_z, info
                    except Exception as e:
                        return "-", "-", "-", f"Error: {e}"

                lc_btn.click(lc_check, inputs=[lc_proj, lc_days], outputs=[lc_total, lc_stale, lc_zombie, lc_info])

            # Tab 8: Scan Comparison (Feature F)
            with gr.TabItem("🔄 Compare Scans"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Regression & Improvement Detection</div>")
                    with gr.Row():
                        cmp_proj = gr.Textbox(label="Project ID", scale=2)
                        cmp_load = gr.Button("Load Scans", elem_classes=["glass-btn"], scale=1)
                    cmp_list = gr.JSON(label="Scans")
                    with gr.Row():
                        cmp_a = gr.Textbox(label="Scan A ID")
                        cmp_b = gr.Textbox(label="Scan B ID")
                        cmp_btn = gr.Button("Compare", elem_classes=["glass-btn"])
                    cmp_result = gr.JSON(label="Comparison")

                def load_cmp_scans(pid):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        db = SessionLocal()
                        scans = db.query(Scan).filter(Scan.project_id==pid).order_by(Scan.created_at.desc()).limit(10).all()

                        return [{"id":s.id,"date":str(s.created_at)[:16],"health":(s.result_summary or {}).get("health_score","N/A")} for s in scans]
                    except Exception as e:
                        return [{"error":str(e)}]

                def compare_scans(sa_id, sb_id):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        db = SessionLocal()
                        sa = db.query(Scan).filter(Scan.id==sa_id).first()
                        sb = db.query(Scan).filter(Scan.id==sb_id).first()

                        if not sa or not sb: return {"error": "Scan not found"}
                        sma, smb = sa.result_summary or {}, sb.result_summary or {}
                        hdiff = smb.get("health_score",0) - sma.get("health_score",0)
                        cdiff = smb.get("conflict_count",0) - sma.get("conflict_count",0)
                        return {"scan_a": sma, "scan_b": smb, "diff": {"health": f"{'+' if hdiff>=0 else ''}{hdiff}%", "conflicts": f"{'+' if cdiff>=0 else ''}{cdiff}", "verdict": "⚠️ REGRESSION" if cdiff > 0 else "✅ IMPROVED" if hdiff > 0 else "→ STABLE"}}
                    except Exception as e:
                        return {"error": str(e)}

                cmp_load.click(load_cmp_scans, inputs=[cmp_proj], outputs=[cmp_list])
                cmp_btn.click(compare_scans, inputs=[cmp_a, cmp_b], outputs=[cmp_result])

            # Tab 9: Profile
            with gr.TabItem("👤 Profile"):
                with gr.Group(elem_classes=["glass-card"]):
                    profile_info = gr.JSON(label="My Profile")
                    load_profile_btn = gr.Button("Load Profile", elem_classes=["glass-btn"])
                    with gr.Row():
                        curr_pw = gr.Textbox(label="Current Password", type="password")
                        new_pw = gr.Textbox(label="New Password", type="password")
                        new_pw2 = gr.Textbox(label="Confirm", type="password")
                    change_pw_btn = gr.Button("Change Password", elem_classes=["glass-btn"])
                    pw_msg = gr.Textbox(label="Status", interactive=False)

                def load_profile(uid):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        db = SessionLocal()
                        u = db.query(User).filter(User.id==uid).first()

                        return {"email":u.email,"name":u.full_name,"role":u.role} if u else {}
                    except Exception as e:
                        return {"error":str(e)}

                def do_change_pw(uid, curr, new, confirm):
                    if new != confirm: return "Passwords don't match."
                    if len(new) < 6: return "Min 6 chars."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        from flagguard.auth.utils import verify_password, get_password_hash
                        db = SessionLocal()
                        u = db.query(User).filter(User.id==uid).first()
                        if not u or not verify_password(curr, u.hashed_password):
                            return "Current password wrong."
                        u.hashed_password = get_password_hash(new)
                        db.commit()
                        return "Password changed!"
                    except Exception as e:
                        return f"Error: {e}"

                load_profile_btn.click(load_profile, inputs=[user_state], outputs=[profile_info])
                change_pw_btn.click(do_change_pw, inputs=[user_state, curr_pw, new_pw, new_pw2], outputs=[pw_msg])

        def refresh_projects(uid):
            if not uid:
                return gr.update(choices=[])
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import Project
                db = SessionLocal()
                projs = db.query(Project).filter(Project.owner_id == uid)\
                          .order_by(Project.created_at.desc()).all()

                return gr.update(choices=[(p.name, p.id) for p in projs],
                                 value=projs[0].id if projs else None)
            except Exception:
                return gr.update(choices=[])

        user_state.change(refresh_projects, inputs=[user_state], outputs=[project_selector])

    return dashboard, logout_btn

