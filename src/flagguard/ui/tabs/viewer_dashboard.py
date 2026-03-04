"""Viewer Dashboard — Read-only access only.

Features: View own projects, scan history, flag charts, dependency graph (read-only),
markdown report, flag lifecycle (read-only), AI chat, notifications, profile.
"""

import gradio as gr
from flagguard.ui.helpers import run_analysis
from flagguard.ui.tabs.header import create_shared_header


def create_viewer_dashboard(app: gr.Blocks, user_state: gr.State):
    """Build the Viewer dashboard. Returns the dashboard Group component."""

    with gr.Group(visible=False) as dashboard:

        # ── header (notification bell + dark/light toggle built in) ────────
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                header_html, logout_btn = create_shared_header("viewer", user_state)

        # ── role banner ──────────────────────────────────────────────────────
        gr.HTML("""
        <div class='role-banner-viewer'>
            <b style='color:#94a3b8;'>👁 You are a Viewer</b> — Read-only access.
            You can view projects, scan results, flag health, and chat with AI.
            <br>To create projects or run scans, contact your admin to upgrade to <b>Analyst</b>.
        </div>""")

        # ── project selector (own projects only) ─────────────────────────────
        with gr.Row():
            project_selector = gr.Dropdown(label="My Projects", choices=[], interactive=True, scale=4)
            refresh_proj_btn = gr.Button("↻ Refresh", elem_classes=["glass-btn"], size="sm", scale=1)

        with gr.Row():
            # metrics
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

        gr.HTML("<div style='margin:20px 0;'></div>")

        # ── tabs ─────────────────────────────────────────────────────────────
        with gr.Tabs():

            # --- Tab 1: Scan History ---
            with gr.TabItem("📋 Scan History"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Recent Scans (Read-Only)</div>")
                    history_table = gr.JSON(label="Scan History")
                    load_history_btn = gr.Button("Load Scan History", elem_classes=["glass-btn"])

                    def load_scan_history(proj_id):
                        if not proj_id:
                            return []
                        try:
                            from flagguard.core.db import SessionLocal
                            from flagguard.core.models.tables import Scan
                            db = SessionLocal()
                            scans = db.query(Scan).filter(
                                Scan.project_id == proj_id
                            ).order_by(Scan.created_at.desc()).limit(20).all()
                            db.close()
                            return [{"id": s.id, "status": s.status,
                                     "triggered_by": s.triggered_by,
                                     "health": (s.result_summary or {}).get("health_score", "N/A"),
                                     "flags": (s.result_summary or {}).get("flag_count", 0),
                                     "date": str(s.created_at)} for s in scans]
                        except Exception as e:
                            return [{"error": str(e)}]

                    load_history_btn.click(load_scan_history, inputs=[project_selector], outputs=[history_table])

            # --- Tab 2: Analytics ---
            with gr.TabItem("📊 Analytics"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes=["glass-card"]):
                            plot_status = gr.Plot(label="Flag Status")
                    with gr.Column(scale=1):
                        with gr.Group(elem_classes=["glass-card"]):
                            plot_severity = gr.Plot(label="Conflict Severity")

            # --- Tab 3: Dependency Graph ---
            with gr.TabItem("🔗 Dependency Graph"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Dependency Graph (Read-Only)</div>")
                    graph_html = gr.HTML("<div style='text-align:center;color:#94a3b8;padding:40px;'>Run an analysis to see the dependency graph.</div>")
                with gr.Accordion("Mermaid Code", open=False):
                    mermaid_code_display = gr.Code(label="Mermaid Definition", language=None, lines=15, interactive=False)

            # --- Tab 4: Report ---
            with gr.TabItem("📄 Report"):
                with gr.Group(elem_classes=["glass-card"]):
                    report_md = gr.Markdown("No scan data. Ask an Analyst or Admin to run a scan on your project.")

            # --- Tab 5: Flag Lifecycle (Read-Only) ---
            with gr.TabItem("⏳ Flag Lifecycle"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Flag Lifecycle Health (Read-Only)</div>")
                    gr.HTML("""
                    <div style='background:rgba(148,163,184,0.08);border:1px solid rgba(148,163,184,0.2);
                                border-radius:8px;padding:12px;margin-bottom:16px;font-size:0.85rem;color:#94a3b8;'>
                        ℹ️ Viewers can view flag lifecycle status. 
                        Cleanup actions require Analyst or Admin access.
                    </div>""")
                    with gr.Row():
                        lc_proj = gr.Textbox(label="Project ID")
                        lc_btn = gr.Button("Check Lifecycle", elem_classes=["glass-btn"])
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_total = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Total</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_active = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Active</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_stale = gr.HTML("<div class='metric-value' style='color:#f59e0b'>-</div><div class='metric-label'>Stale</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                lc_zombie = gr.HTML("<div class='metric-value' style='color:#ef4444'>-</div><div class='metric-label'>Zombie</div>")
                    lc_info = gr.Markdown("Enter a Project ID and click Check Lifecycle.")

                    def check_lc_viewer(proj_id):
                        import requests
                        try:
                            resp = requests.get(f"http://localhost:8000/api/v1/lifecycle/report/{proj_id}",
                                                params={"stale_threshold_days": 30})
                            d = resp.json() if resp.status_code < 400 else {}
                            h_t = f"<div class='metric-value'>{d.get('total_flags',0)}</div><div class='metric-label'>Total</div>"
                            h_a = f"<div class='metric-value'>{d.get('active_flags',0)}</div><div class='metric-label'>Active</div>"
                            h_s = f"<div class='metric-value' style='color:#f59e0b'>{d.get('stale_flags',0)}</div><div class='metric-label'>Stale</div>"
                            h_z = f"<div class='metric-value' style='color:#ef4444'>{d.get('zombie_flags',0)}</div><div class='metric-label'>Zombie</div>"
                            info = "### Cleanup Suggestions (contact Analyst to act on these)\n"
                            for s in d.get('cleanup_suggestions', []):
                                info += f"- {s}\n"
                            return h_t, h_a, h_s, h_z, info
                        except Exception as e:
                            return "-", "-", "-", "-", f"Error: {e}"

                    lc_btn.click(check_lc_viewer, inputs=[lc_proj],
                                 outputs=[lc_total, lc_active, lc_stale, lc_zombie, lc_info])

            # --- Tab 6: Flag Search ---
            with gr.TabItem("🔍 Flag Search"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Search & Filter Flags</div>")
                    with gr.Row():
                        search_query = gr.Textbox(label="Search Flag Name", placeholder="e.g. dark_mode, new_checkout", scale=3)
                        search_status = gr.Dropdown(label="Status", choices=["all", "enabled", "disabled"], value="all", scale=1)
                        search_btn = gr.Button("Search", elem_classes=["glass-btn"], scale=1)
                    search_results = gr.JSON(label="Results")

                    def search_flags(query, status_filter):
                        try:
                            from flagguard.ui.helpers import load_history
                            # Search in scan history
                            history = load_history()
                            results = []
                            for entry in history[:10]:
                                if query.lower() in entry.get("config_file", "").lower():
                                    results.append(entry)
                            return results if results else [{"message": "No matching flags found in scan history. Run an analysis first."}]
                        except Exception as e:
                            return [{"error": str(e)}]

                    search_btn.click(search_flags, inputs=[search_query, search_status], outputs=[search_results])

            # --- Tab 7: AI Chat ---
            with gr.TabItem("🤖 AI Chat"):
                from flagguard.ui.tabs.chat import create_chat_tab
                create_chat_tab(app)

            # --- Tab 8: Profile ---
            with gr.TabItem("👤 Profile"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>My Profile</div>")
                    profile_info = gr.JSON(label="Account Details")
                    load_profile_btn = gr.Button("Load Profile", elem_classes=["glass-btn"])
                    gr.HTML("<div style='margin:20px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Change Password</div>")
                    with gr.Row():
                        curr_pw = gr.Textbox(label="Current Password", type="password", scale=1)
                        new_pw = gr.Textbox(label="New Password", type="password", scale=1)
                        new_pw2 = gr.Textbox(label="Confirm New Password", type="password", scale=1)
                    change_pw_btn = gr.Button("Change Password", elem_classes=["glass-btn"])
                    pw_msg = gr.Textbox(label="Status", interactive=False)

                    def load_profile(uid):
                        try:
                            from flagguard.core.db import SessionLocal
                            from flagguard.core.models.tables import User
                            db = SessionLocal()
                            user = db.query(User).filter(User.id == uid).first()
                            db.close()
                            if not user:
                                return {}
                            return {"email": user.email, "name": user.full_name,
                                    "role": user.role, "active": user.is_active,
                                    "joined": str(user.created_at)}
                        except Exception as e:
                            return {"error": str(e)}

                    def do_change_pw(uid, curr, new, confirm):
                        if new != confirm:
                            return "Passwords do not match."
                        if len(new) < 6:
                            return "Password must be at least 6 characters."
                        try:
                            from flagguard.core.db import SessionLocal
                            from flagguard.core.models.tables import User
                            from flagguard.auth.utils import verify_password, get_password_hash
                            db = SessionLocal()
                            user = db.query(User).filter(User.id == uid).first()
                            if not user or not verify_password(curr, user.hashed_password):
                                db.close()
                                return "Current password is incorrect."
                            user.hashed_password = get_password_hash(new)
                            db.commit()
                            db.close()
                            return "Password changed successfully."
                        except Exception as e:
                            return f"Error: {e}"

                    load_profile_btn.click(load_profile, inputs=[user_state], outputs=[profile_info])
                    change_pw_btn.click(do_change_pw, inputs=[user_state, curr_pw, new_pw, new_pw2], outputs=[pw_msg])

        # ── handlers ────────────────────────────────────────────────────────
        def refresh_projects(uid):
            if not uid:
                return gr.update(choices=[])
            try:
                from flagguard.services.project import ProjectService
                svc = ProjectService()
                projs = svc.get_projects_for_user(uid)
                return gr.update(choices=[(p.name, p.id) for p in projs],
                                 value=projs[0].id if projs else None)
            except Exception:
                return gr.update(choices=[])

        user_state.change(refresh_projects, inputs=[user_state], outputs=[project_selector])
        refresh_proj_btn.click(refresh_projects, inputs=[user_state], outputs=[project_selector])

    return dashboard, logout_btn, plot_status, plot_severity, graph_html, mermaid_code_display, report_md, val_flags, val_active, val_conflicts, val_health
