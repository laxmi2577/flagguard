"""Admin Dashboard — Full system control.

Includes everything Analyst has + User Approvals, User Management,
Audit Log, Platform Analytics, Plugin Management, CI/CD Gate, Password Reset.
All Tier 2 and Tier 3 features are present here.
"""

import gradio as gr
from flagguard.ui.helpers import run_analysis
from flagguard.ui.tabs.header import create_shared_header


def create_admin_dashboard(app: gr.Blocks, user_state: gr.State):
    with gr.Group(visible=False) as dashboard:

        # ── Header (notification bell + dark/light toggle built in) ─────────
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                header_html, logout_btn = create_shared_header("admin", user_state)

        # ── Role Banner ───────────────────────────────────────────────────────
        gr.HTML("""
        <div class='role-banner-admin'>
            <b style='color:#ef4444;'>👑 You are an Admin</b> — Full system access.
            You can manage users, approve signups, view audit logs, manage plugins,
            run CI/CD gates, and access all analyst features.
        </div>""")

        # ── Summary Metrics ───────────────────────────────────────────────────
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

        # ── Tabs ──────────────────────────────────────────────────────────────
        with gr.Tabs():

            # ─── Tab 1: User Approvals (Admin-only) ───────────────────────────
            with gr.TabItem("✅ User Approvals"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Pending Signup Requests</div>")
                    approval_refresh_btn = gr.Button("Refresh Requests", elem_classes=["glass-btn"])
                    pending_table = gr.JSON(label="Pending Requests")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Approve or Reject</div>")
                    with gr.Row():
                        approval_id = gr.Textbox(label="Request ID (from table above)", scale=3)
                        approve_btn = gr.Button("✅ Approve", elem_classes=["success-btn glass-btn"], scale=1)
                        reject_btn  = gr.Button("❌ Reject",  elem_classes=["danger-btn glass-btn"], scale=1)
                    reject_reason = gr.Textbox(label="Rejection Reason (optional)", placeholder="e.g. Incomplete application", scale=3)
                    approval_msg = gr.Textbox(label="Status", interactive=False)

                def load_pending(_uid):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PendingUser
                        db = SessionLocal()
                        pending = db.query(PendingUser).filter(PendingUser.status == "pending")\
                                     .order_by(PendingUser.requested_at.desc()).all()
                        db.close()
                        return [{"id": p.id, "name": p.full_name, "email": p.email,
                                 "role": p.requested_role, "reason": p.reason,
                                 "requested": str(p.requested_at)[:16]} for p in pending]
                    except Exception as e:
                        return [{"error": str(e)}]

                def approve_user(pending_id, uid):
                    if not pending_id:
                        return "Enter a Request ID"
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PendingUser, User, Notification
                        from flagguard.auth.utils import get_password_hash
                        from datetime import datetime as dt
                        db = SessionLocal()
                        p = db.query(PendingUser).filter(PendingUser.id == pending_id.strip()).first()
                        if not p:
                            db.close(); return "Request not found."
                        if p.status != "pending":
                            db.close(); return f"Already {p.status}."
                        new_user = User(email=p.email, hashed_password=p.hashed_password,
                                        full_name=p.full_name, role=p.requested_role, is_active=True)
                        db.add(new_user)
                        p.status = "approved"; p.reviewed_at = dt.utcnow(); p.reviewed_by = uid
                        db.commit(); db.refresh(new_user)
                        notif = Notification(user_id=new_user.id, title="Access Approved",
                            message=f"Your {p.requested_role} access has been approved! You can now sign in.",
                            type="success")
                        db.add(notif); db.commit(); db.close()
                        return f"✅ Approved! {p.email} can now login as {p.requested_role}."
                    except Exception as e:
                        return f"Error: {e}"

                def reject_user(pending_id, reason, uid):
                    if not pending_id:
                        return "Enter a Request ID"
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PendingUser
                        from datetime import datetime as dt
                        db = SessionLocal()
                        p = db.query(PendingUser).filter(PendingUser.id == pending_id.strip()).first()
                        if not p:
                            db.close(); return "Request not found."
                        if p.status != "pending":
                            db.close(); return f"Already {p.status}."
                        p.status = "rejected"; p.reviewed_at = dt.utcnow()
                        p.reviewed_by = uid; p.reason = reason or "Request denied by admin."
                        db.commit(); db.close()
                        return f"❌ Rejected request for {p.email}."
                    except Exception as e:
                        return f"Error: {e}"

                approval_refresh_btn.click(load_pending, inputs=[user_state], outputs=[pending_table])
                approve_btn.click(approve_user, inputs=[approval_id, user_state], outputs=[approval_msg])
                reject_btn.click(reject_user, inputs=[approval_id, reject_reason, user_state], outputs=[approval_msg])

            # ─── Tab 2: User Management ───────────────────────────────────────
            with gr.TabItem("👥 User Management"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>All Users</div>")
                    users_refresh_btn = gr.Button("Load All Users", elem_classes=["glass-btn"])
                    users_table = gr.JSON(label="Users")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Change Role</div>")
                    with gr.Row():
                        role_user_id = gr.Textbox(label="User ID", scale=3)
                        role_new = gr.Dropdown(label="New Role", choices=["viewer","analyst","admin"], scale=1)
                        role_btn = gr.Button("Change Role", elem_classes=["glass-btn"], scale=1)
                    role_msg = gr.Textbox(label="Status", interactive=False)
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Reset User Password</div>")
                    with gr.Row():
                        reset_uid = gr.Textbox(label="User ID", scale=2)
                        reset_pw  = gr.Textbox(label="New Password", type="password", scale=2)
                        reset_btn = gr.Button("Reset Password", elem_classes=["danger-btn glass-btn"], scale=1)
                    reset_msg = gr.Textbox(label="Status", interactive=False)
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Deactivate Account</div>")
                    with gr.Row():
                        deact_uid = gr.Textbox(label="User ID", scale=3)
                        deact_btn = gr.Button("Deactivate", elem_classes=["danger-btn glass-btn"], scale=1)
                    deact_msg = gr.Textbox(label="Status", interactive=False)

                def load_users(_):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        db = SessionLocal()
                        users = db.query(User).order_by(User.created_at.desc()).all()
                        db.close()
                        return [{"id": u.id, "email": u.email, "name": u.full_name,
                                 "role": u.role, "active": u.is_active,
                                 "joined": str(u.created_at)[:10]} for u in users]
                    except Exception as e:
                        return [{"error": str(e)}]

                def change_role(target_uid, new_role):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        db = SessionLocal()
                        u = db.query(User).filter(User.id == target_uid.strip()).first()
                        if not u: db.close(); return "User not found."
                        u.role = new_role; db.commit(); db.close()
                        return f"Role updated to {new_role}."
                    except Exception as e:
                        return f"Error: {e}"

                def reset_password(target_uid, new_pw):
                    if len(new_pw) < 6: return "Min 6 characters."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        from flagguard.auth.utils import get_password_hash
                        db = SessionLocal()
                        u = db.query(User).filter(User.id == target_uid.strip()).first()
                        if not u: db.close(); return "User not found."
                        u.hashed_password = get_password_hash(new_pw)
                        db.commit(); db.close()
                        return "Password reset successfully."
                    except Exception as e:
                        return f"Error: {e}"

                def deactivate_user(target_uid, my_uid):
                    if target_uid.strip() == my_uid:
                        return "Cannot deactivate yourself."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        db = SessionLocal()
                        u = db.query(User).filter(User.id == target_uid.strip()).first()
                        if not u: db.close(); return "User not found."
                        u.is_active = False; db.commit(); db.close()
                        return f"Account {u.email} deactivated."
                    except Exception as e:
                        return f"Error: {e}"

                users_refresh_btn.click(load_users, inputs=[user_state], outputs=[users_table])
                role_btn.click(change_role, inputs=[role_user_id, role_new], outputs=[role_msg])
                reset_btn.click(reset_password, inputs=[reset_uid, reset_pw], outputs=[reset_msg])
                deact_btn.click(deactivate_user, inputs=[deact_uid, user_state], outputs=[deact_msg])

            # ─── Tab 3: Audit Log ─────────────────────────────────────────────
            with gr.TabItem("📋 Audit Log"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>System Audit Trail</div>")
                    with gr.Row():
                        audit_action = gr.Dropdown(label="Action", choices=["","create","update","delete","scan","login","export","approve_signup","reject_signup","reset_password"], value="", scale=1)
                        audit_resource = gr.Dropdown(label="Resource", choices=["","project","scan","webhook","environment","plugin","user","pending_user"], value="", scale=1)
                        audit_refresh = gr.Button("Refresh", elem_classes=["glass-btn"], scale=1)
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                audit_total_html = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Total Events</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                audit_today_html = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Today</div>")
                    audit_table = gr.JSON(label="Audit Events (latest 50)")

                def load_audit(action_f, resource_f):
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import AuditLog
                        from datetime import datetime as dt, date
                        db = SessionLocal()
                        q = db.query(AuditLog)
                        if action_f:   q = q.filter(AuditLog.action == action_f)
                        if resource_f: q = q.filter(AuditLog.resource_type == resource_f)
                        total = q.count()
                        today_count = db.query(AuditLog).filter(
                            AuditLog.created_at >= dt.combine(date.today(), dt.min.time())
                        ).count()
                        logs = q.order_by(AuditLog.created_at.desc()).limit(50).all()
                        db.close()
                        h_total = f"<div class='metric-value'>{total}</div><div class='metric-label'>Total Events</div>"
                        h_today = f"<div class='metric-value'>{today_count}</div><div class='metric-label'>Today</div>"
                        rows = [{"action": l.action, "resource": l.resource_type,
                                 "resource_id": l.resource_id, "user_id": l.user_id,
                                 "date": str(l.created_at)[:16]} for l in logs]
                        return h_total, h_today, rows
                    except Exception as e:
                        return "-", "-", [{"error": str(e)}]

                audit_refresh.click(load_audit, inputs=[audit_action, audit_resource],
                                    outputs=[audit_total_html, audit_today_html, audit_table])

            # ─── Tab 4: Platform Analytics ────────────────────────────────────
            with gr.TabItem("📊 Analytics"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Platform-Wide Statistics</div>")
                    analytics_btn = gr.Button("Load Overview", elem_classes=["glass-btn"])
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                an_users = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Users</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                an_projects = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Projects</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                an_scans = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Scans</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                an_health = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Avg Health</div>")
                    analytics_raw = gr.JSON(label="Full Overview")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Leaderboard</div>")
                    leaderboard_btn = gr.Button("Load Leaderboard", elem_classes=["glass-btn"])
                    leaderboard_data = gr.JSON(label="Leaderboard")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Project Health Cards</div>")
                    health_btn = gr.Button("Load Project Health", elem_classes=["glass-btn"])
                    health_data = gr.JSON(label="Project Health")

                def load_overview():
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User, Project, Scan
                        db = SessionLocal()
                        users_count = db.query(User).count()
                        projs_count = db.query(Project).count()
                        scans_count = db.query(Scan).count()
                        db.close()
                        overview = {"total_users": users_count, "total_projects": projs_count,
                                    "total_scans": scans_count, "status": "operational"}
                        h_u = f"<div class='metric-value'>{users_count}</div><div class='metric-label'>Users</div>"
                        h_p = f"<div class='metric-value'>{projs_count}</div><div class='metric-label'>Projects</div>"
                        h_s = f"<div class='metric-value'>{scans_count}</div><div class='metric-label'>Scans</div>"
                        h_h = f"<div class='metric-value'>N/A</div><div class='metric-label'>Avg Health</div>"
                        return h_u, h_p, h_s, h_h, overview
                    except Exception as e:
                        return "-","-","-","-", {"error": str(e)}

                def load_leaderboard():
                    import requests
                    try:
                        return requests.get("http://localhost:8000/api/v1/analytics/leaderboard").json()
                    except Exception as e:
                        return {"error": str(e)}

                def load_health():
                    import requests
                    try:
                        return requests.get("http://localhost:8000/api/v1/analytics/project-health").json()
                    except Exception as e:
                        return {"error": str(e)}

                analytics_btn.click(load_overview, outputs=[an_users, an_projects, an_scans, an_health, analytics_raw])
                leaderboard_btn.click(load_leaderboard, outputs=[leaderboard_data])
                health_btn.click(load_health, outputs=[health_data])

            # ─── Tab 5: Plugin Management ─────────────────────────────────────
            with gr.TabItem("🔌 Plugins"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>Registered Plugins</div>")
                    plugins_refresh = gr.Button("Load Plugins", elem_classes=["glass-btn"])
                    plugins_table = gr.JSON(label="Plugins")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Register New Plugin</div>")
                    with gr.Row():
                        plug_name = gr.Textbox(label="Plugin Name", scale=2)
                        plug_type = gr.Dropdown(label="Type", choices=["parser","rule"], scale=1)
                        plug_version = gr.Textbox(label="Version", value="1.0.0", scale=1)
                    plug_desc = gr.Textbox(label="Description")
                    plug_register_btn = gr.Button("Register Plugin", elem_classes=["glass-btn"])
                    plug_msg = gr.Textbox(label="Status", interactive=False)
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Toggle / Remove Plugin</div>")
                    with gr.Row():
                        plug_toggle_id = gr.Textbox(label="Plugin ID", scale=2)
                        plug_enabled = gr.Checkbox(label="Enabled", value=True, scale=1)
                        plug_toggle_btn = gr.Button("Toggle", elem_classes=["glass-btn"], scale=1)
                        plug_delete_btn = gr.Button("Remove", elem_classes=["danger-btn glass-btn"], scale=1)
                    plug_toggle_msg = gr.Textbox(label="Status", interactive=False)

                def load_plugins():
                    import requests
                    try:
                        return requests.get("http://localhost:8000/api/v1/plugins").json()
                    except Exception as e:
                        return {"error": str(e)}

                def register_plugin(name, ptype, version, desc):
                    import requests
                    try:
                        r = requests.post("http://localhost:8000/api/v1/plugins",
                                          json={"name": name, "type": ptype, "version": version, "description": desc})
                        return f"Registered: {name}" if r.status_code < 400 else f"Error: {r.text}"
                    except Exception as e:
                        return f"Error: {e}"

                def toggle_plugin(pid, enabled):
                    import requests
                    try:
                        r = requests.put(f"http://localhost:8000/api/v1/plugins/{pid}", json={"enabled": enabled})
                        return f"Plugin {'enabled' if enabled else 'disabled'}." if r.status_code < 400 else f"Error: {r.text}"
                    except Exception as e:
                        return f"Error: {e}"

                def delete_plugin(pid):
                    import requests
                    try:
                        r = requests.delete(f"http://localhost:8000/api/v1/plugins/{pid}")
                        return "Plugin removed." if r.status_code < 400 else f"Error: {r.text}"
                    except Exception as e:
                        return f"Error: {e}"

                plugins_refresh.click(load_plugins, outputs=[plugins_table])
                plug_register_btn.click(register_plugin, inputs=[plug_name, plug_type, plug_version, plug_desc], outputs=[plug_msg])
                plug_toggle_btn.click(toggle_plugin, inputs=[plug_toggle_id, plug_enabled], outputs=[plug_toggle_msg])
                plug_delete_btn.click(delete_plugin, inputs=[plug_toggle_id], outputs=[plug_toggle_msg])

            # ─── Tab 6: CI/CD Gate ────────────────────────────────────────────
            with gr.TabItem("🚦 CI/CD Gate"):
                with gr.Group(elem_classes=["glass-card"]):
                    gr.HTML("<div class='sidebar-title'>CI/CD Health Gate Check</div>")
                    gr.HTML("""
                    <div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);
                                border-radius:8px;padding:12px;margin-bottom:16px;font-size:0.85rem;color:#f59e0b;'>
                        ⚠️ This check can be used in CI/CD pipelines to block merges when flag conflicts are detected.
                        Block pipeline if health score drops below threshold.
                    </div>""")
                    with gr.Row():
                        cicd_proj = gr.Textbox(label="Project ID", scale=3)
                        cicd_threshold = gr.Slider(label="Min Health % (gate)", minimum=0, maximum=100, value=80, scale=2)
                        cicd_btn = gr.Button("Run Gate Check", elem_classes=["glass-btn"], scale=1)
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                gate_status_html = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Gate Status</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                gate_health_html = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Health Score</div>")
                    cicd_result = gr.JSON(label="Full Gate Report")

                def run_gate(pid, threshold):
                    import requests
                    try:
                        r = requests.get(f"http://localhost:8000/api/v1/scheduler/cicd-gate/{pid}",
                                         params={"min_health": int(threshold)})
                        d = r.json() if r.status_code < 400 else {}
                        passed = d.get("gate_passed", False)
                        health = d.get("current_health", 0)
                        status_color = "#30d158" if passed else "#ef4444"
                        status_text = "PASS" if passed else "FAIL"
                        h_s = f"<div class='metric-value' style='color:{status_color}'>{status_text}</div><div class='metric-label'>Gate Status</div>"
                        h_h = f"<div class='metric-value'>{health}%</div><div class='metric-label'>Health Score</div>"
                        return h_s, h_h, d
                    except Exception as e:
                        return "-", "-", {"error": str(e)}

                cicd_btn.click(run_gate, inputs=[cicd_proj, cicd_threshold], outputs=[gate_status_html, gate_health_html, cicd_result])

            # ─── Tab 7: Analysis (Admin also runs scans) ──────────────────────
            with gr.TabItem("⚡ Analysis"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes=["frosted-sidebar"]):
                        gr.HTML("<div class='sidebar-title'>All Projects</div>")
                        project_selector = gr.Dropdown(label="", choices=[], interactive=True)
                        with gr.Row():
                            new_proj_name = gr.Textbox(label="New Project")
                            create_proj_btn = gr.Button("+ Create", elem_classes=["glass-btn"], size="sm")
                        proj_msg = gr.Textbox(interactive=False, show_label=False)
                        gr.HTML("<div style='margin:12px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                        file_input = gr.File(label="Flag Manifest", file_types=[".json",".yaml"])
                        source_input = gr.File(label="Source Archive", file_types=[".zip"])
                        use_llm = gr.Checkbox(label="AI Analysis", value=True)
                        analyze_btn = gr.Button("⚡ Run Analysis", elem_classes=["glass-btn"])
                    with gr.Column(scale=4):
                        with gr.Tabs():
                            with gr.TabItem("Charts"):
                                with gr.Row():
                                    with gr.Column():
                                        plot_status = gr.Plot(label="Flag Status")
                                    with gr.Column():
                                        plot_severity = gr.Plot(label="Severity")
                            with gr.TabItem("Dependency Graph"):
                                graph_html = gr.HTML("<div style='text-align:center;color:#94a3b8;padding:40px;'>Run analysis.</div>")
                                with gr.Accordion("Mermaid Code", open=False):
                                    mermaid_code = gr.Code(label="", language=None, lines=12, interactive=False)
                            with gr.TabItem("Report"):
                                report_md = gr.Markdown("No scan data.")

                def create_project(name, uid):
                    if not name: return gr.update(), "Enter a project name."
                    try:
                        from flagguard.services.project import ProjectService
                        svc = ProjectService()
                        p = svc.create_project(name, uid)
                        projs = svc.get_projects_for_user(uid)
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
                    outputs=[val_flags, val_active, val_conflicts, val_health, plot_status, plot_severity, report_md, graph_html, mermaid_code])

            # ─── Tab 8: Environments ──────────────────────────────────────────
            with gr.TabItem("🌍 Environments"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        env_proj = gr.Textbox(label="Project ID", scale=2)
                        env_name_inp = gr.Textbox(label="Name", placeholder="dev/staging/prod", scale=2)
                        env_btn = gr.Button("Create", elem_classes=["glass-btn"], scale=1)
                    env_overrides = gr.Textbox(label="Flag Overrides (JSON)", lines=3)
                    env_result = gr.JSON(label="Result")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    with gr.Row():
                        drift_a = gr.Textbox(label="Env A ID", scale=1)
                        drift_b = gr.Textbox(label="Env B ID", scale=1)
                        drift_btn = gr.Button("Compare Drift", elem_classes=["glass-btn"], scale=1)
                    drift_result = gr.JSON(label="Drift Report")

                def create_env(pid, name, overrides):
                    import requests, json
                    try:
                        ovr = json.loads(overrides) if overrides.strip() else {}
                        r = requests.post(f"http://localhost:8000/api/v1/environments/project/{pid}", json={"name": name, "flag_overrides": ovr})
                        return r.json()
                    except Exception as e:
                        return {"error": str(e)}

                env_btn.click(create_env, inputs=[env_proj, env_name_inp, env_overrides], outputs=[env_result])
                drift_btn.click(lambda a,b: __import__('requests').get("http://localhost:8000/api/v1/environments/compare", params={"env_a_id":a,"env_b_id":b}).json(), inputs=[drift_a, drift_b], outputs=[drift_result])

            # ─── Tab 9: Reports ───────────────────────────────────────────────
            with gr.TabItem("📑 Reports"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        rep_proj = gr.Textbox(label="Project ID", scale=3)
                        rep_fmt = gr.Dropdown(label="Format", choices=["json","csv","markdown"], value="json", scale=1)
                        rep_btn = gr.Button("Generate", elem_classes=["glass-btn"], scale=1)
                    rep_result = gr.JSON(label="Report")
                    exec_proj = gr.Textbox(label="Project ID (Executive Summary)")
                    exec_btn = gr.Button("Executive Summary", elem_classes=["glass-btn"])
                    exec_result = gr.JSON(label="Summary")

                rep_btn.click(lambda p,f: __import__('requests').post("http://localhost:8000/api/v1/reports/generate", json={"project_id":p,"format":f}).json(), inputs=[rep_proj, rep_fmt], outputs=[rep_result])
                exec_btn.click(lambda p: __import__('requests').get(f"http://localhost:8000/api/v1/reports/executive-summary/{p}").json(), inputs=[exec_proj], outputs=[exec_result])

            # ─── Tab 10: IaC Scan ─────────────────────────────────────────────
            with gr.TabItem("🏗️ IaC Scan"):
                with gr.Group(elem_classes=["glass-card"]):
                    iac_file = gr.File(label="Upload IaC File (.tf, .yaml, .json)", file_types=[".tf",".yaml",".yml",".json"])
                    iac_btn = gr.Button("Analyze", elem_classes=["glass-btn"])
                    iac_result = gr.JSON(label="Detected Flags")

                def analyze_iac(file):
                    import requests
                    if not file: return {"error": "No file"}
                    try:
                        with open(file.name, "rb") as f:
                            r = requests.post("http://localhost:8000/api/v1/iac/analyze", files={"iac_file": (file.name, f)})
                        return r.json()
                    except Exception as e:
                        return {"error": str(e)}

                iac_btn.click(analyze_iac, inputs=[iac_file], outputs=[iac_result])

            # ─── Tab 11: Profile ──────────────────────────────────────────────
            with gr.TabItem("👤 Profile"):
                with gr.Group(elem_classes=["glass-card"]):
                    profile_info = gr.JSON(label="My Admin Profile")
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
                        db.close()
                        return {"email":u.email,"name":u.full_name,"role":u.role,"joined":str(u.created_at)[:10]} if u else {}
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
                            db.close(); return "Current password wrong."
                        u.hashed_password = get_password_hash(new)
                        db.commit(); db.close()
                        return "Password changed!"
                    except Exception as e:
                        return f"Error: {e}"

                load_profile_btn.click(load_profile, inputs=[user_state], outputs=[profile_info])
                change_pw_btn.click(do_change_pw, inputs=[user_state, curr_pw, new_pw, new_pw2], outputs=[pw_msg])

        # ── Project Refresh ───────────────────────────────────────────────────
        def refresh_all_projects(uid):
            """Admin sees ALL projects."""
            if not uid: return gr.update(choices=[])
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import Project
                db = SessionLocal()
                projs = db.query(Project).order_by(Project.created_at.desc()).all()
                db.close()
                return gr.update(choices=[(p.name, p.id) for p in projs],
                                 value=projs[0].id if projs else None)
            except Exception:
                return gr.update(choices=[])

        user_state.change(refresh_all_projects, inputs=[user_state], outputs=[project_selector])

    return dashboard, logout_btn
