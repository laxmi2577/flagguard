"""Admin Dashboard — Full system control.

Includes everything Analyst has + User Approvals, User Management,
Audit Log, Platform Analytics, Plugin Management, CI/CD Gate, Password Reset.
All Tier 2 and Tier 3 features are present here.
"""

import gradio as gr
from flagguard.ui.helpers import run_analysis
from flagguard.ui.tabs.header import create_shared_header

def _load_project_choices():
    """Load all projects as (label, id) tuples for dropdowns."""
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import Project
        db = SessionLocal()
        projs = db.query(Project).order_by(Project.created_at.desc()).all()
        db.close()
        return [
            (f"{p.project_code or p.id[:8]} \u2014 {p.name}", p.id)
            for p in projs
        ]
    except Exception:
        return []

def _load_env_choices():
    """Load all environments as (label, id) tuples for dropdowns."""
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import Environment
        db = SessionLocal()
        envs = db.query(Environment).order_by(Environment.created_at.desc()).all()
        db.close()
        return [(f"{e.name} (Proj: {e.project_id[:8]}...)", e.id) for e in envs]
    except Exception:
        return []

def create_admin_dashboard(app: gr.Blocks, user_state: gr.State):
    with gr.Group(visible=False) as dashboard:

        # ── Header (notification bell + dark/light toggle built in) ─────────
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                header_html, logout_btn, theme_btn = create_shared_header("admin", user_state)

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
                            return "Request not found."
                        if p.status != "pending":
                            return f"Already {p.status}."
                        new_user = User(email=p.email, hashed_password=p.hashed_password,
                                        full_name=p.full_name, role=p.requested_role, is_active=True)
                        db.add(new_user)
                        p.status = "approved"; p.reviewed_at = dt.utcnow(); p.reviewed_by = uid
                        db.commit(); db.refresh(new_user)
                        notif = Notification(user_id=new_user.id, title="Access Approved",
                            message=f"Your {p.requested_role} access has been approved! You can now sign in.",
                            type="success")
                        db.add(notif); db.commit()
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
                            return "Request not found."
                        if p.status != "pending":
                            return f"Already {p.status}."
                        p.status = "rejected"; p.reviewed_at = dt.utcnow()
                        p.reviewed_by = uid; p.reason = reason or "Request denied by admin."
                        db.commit()
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

                    # ── Project Access Assignment (RBAC) ─────────────────────
                    gr.HTML("<div style='margin:16px 0;border-top:2px solid rgba(212,175,55,0.25);'></div>")
                    gr.HTML("<div class='sidebar-title'>🔐 Project Access Assignment</div>")
                    gr.HTML("""
                    <div style='background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.2);
                                border-radius:8px;padding:10px;margin-bottom:12px;font-size:0.85rem;color:#d4af37;'>
                        Assign users to specific projects. Viewers get <b>Read</b> access, Analysts get <b>Write</b> access.
                        Admins see all projects automatically.
                    </div>""")
                    with gr.Row():
                        assign_user = gr.Dropdown(label="Select User", choices=[], interactive=True, scale=2)
                        assign_proj = gr.Dropdown(label="Select Project", choices=[], interactive=True, scale=2)
                        assign_level = gr.Dropdown(label="Access", choices=["read", "write"], value="read", scale=1)
                        assign_btn = gr.Button("Assign", elem_classes=["glass-btn"], scale=1)
                    assign_msg = gr.Textbox(label="Status", interactive=False)
                    with gr.Row():
                        assign_refresh_btn = gr.Button("Load Assignments", elem_classes=["glass-btn"], scale=2)
                        remove_member_id = gr.Textbox(label="Member ID to Remove", scale=2)
                        remove_btn = gr.Button("Remove Access", elem_classes=["danger-btn glass-btn"], scale=1)
                    assignments_table = gr.JSON(label="Current Project Assignments")

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
                        if not u: return "User not found."
                        u.role = new_role; db.commit()
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
                        if not u: return "User not found."
                        u.hashed_password = get_password_hash(new_pw)
                        db.commit()
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
                        if not u: return "User not found."
                        u.is_active = False; db.commit()
                        return f"Account {u.email} deactivated."
                    except Exception as e:
                        return f"Error: {e}"

                # ── RBAC backend functions ───────────────────────────────
                def _load_user_choices():
                    """Load non-admin users for assignment dropdown."""
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User
                        db = SessionLocal()
                        users = db.query(User).filter(
                            User.is_active == True, User.role != "admin"
                        ).order_by(User.email).all()
                        db.close()
                        return [(f"{u.email} ({u.role})", u.id) for u in users]
                    except Exception:
                        return []

                def refresh_assign_dropdowns():
                    """Refresh both user and project dropdowns for assignment."""
                    return (
                        gr.update(choices=_load_user_choices()),
                        gr.update(choices=_load_project_choices()),
                    )

                def assign_access(user_id, project_id, level, admin_uid):
                    if not user_id or not project_id:
                        return "Select both a User and a Project."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import ProjectMember, User, Project
                        db = SessionLocal()
                        # Check for existing assignment
                        existing = db.query(ProjectMember).filter(
                            ProjectMember.user_id == user_id,
                            ProjectMember.project_id == project_id,
                        ).first()
                        if existing:
                            existing.access_level = level
                            db.commit()
                            db.close()
                            return f"✅ Updated access to '{level}' for existing assignment."
                        member = ProjectMember(
                            user_id=user_id,
                            project_id=project_id,
                            access_level=level,
                            assigned_by=admin_uid,
                        )
                        db.add(member)
                        db.commit()
                        # Fetch names for confirmation
                        user = db.query(User).filter(User.id == user_id).first()
                        proj = db.query(Project).filter(Project.id == project_id).first()
                        # Send notification to the assigned user
                        try:
                            from flagguard.core.models.tables import Notification
                            notif = Notification(
                                user_id=user_id,
                                title="Project Assigned",
                                message=f"You have been granted '{level}' access to project {proj.project_code or proj.name}.",
                                type="success",
                            )
                            db.add(notif)
                            db.commit()
                        except Exception:
                            pass  # Don't break assignment if notification fails
                        db.close()
                        return f"✅ Assigned {user.email} → {proj.project_code or proj.name} ({level})"
                    except Exception as e:
                        return f"Error: {e}"

                def load_assignments():
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import ProjectMember, User, Project
                        db = SessionLocal()
                        members = db.query(ProjectMember).all()
                        result = []
                        for m in members:
                            user = db.query(User).filter(User.id == m.user_id).first()
                            proj = db.query(Project).filter(Project.id == m.project_id).first()
                            result.append({
                                "member_id": m.id,
                                "user": user.email if user else m.user_id,
                                "user_role": user.role if user else "?",
                                "project": f"{proj.project_code or '?'} — {proj.name}" if proj else m.project_id,
                                "access": m.access_level,
                                "assigned": str(m.assigned_at)[:16],
                            })
                        db.close()
                        return result if result else [{"message": "No assignments yet"}]
                    except Exception as e:
                        return [{"error": str(e)}]

                def remove_access(member_id):
                    if not member_id:
                        return "Enter a Member ID.", []
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import ProjectMember
                        db = SessionLocal()
                        m = db.query(ProjectMember).filter(ProjectMember.id == member_id.strip()).first()
                        if not m:
                            db.close()
                            return "Member ID not found.", []
                        db.delete(m)
                        db.commit()
                        db.close()
                        return f"✅ Removed access (ID: {member_id.strip()[:8]}...)", load_assignments()
                    except Exception as e:
                        return f"Error: {e}", []

                users_refresh_btn.click(load_users, inputs=[user_state], outputs=[users_table])
                role_btn.click(change_role, inputs=[role_user_id, role_new], outputs=[role_msg])
                reset_btn.click(reset_password, inputs=[reset_uid, reset_pw], outputs=[reset_msg])
                deact_btn.click(deactivate_user, inputs=[deact_uid, user_state], outputs=[deact_msg])
                # RBAC handlers
                users_refresh_btn.click(refresh_assign_dropdowns, outputs=[assign_user, assign_proj])
                assign_btn.click(assign_access, inputs=[assign_user, assign_proj, assign_level, user_state], outputs=[assign_msg])
                assign_refresh_btn.click(load_assignments, outputs=[assignments_table])
                remove_btn.click(remove_access, inputs=[remove_member_id], outputs=[assign_msg, assignments_table])

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

                # ── Audit Stats & Export ──────────────────────────────────
                gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                gr.HTML("<div class='sidebar-title'>Top Actions</div>")
                stats_btn = gr.Button("Load Audit Stats", elem_classes=["glass-btn"])
                stats_result = gr.JSON(label="Top Actions & Users")
                gr.HTML("<div style='margin:12px 0;'></div>")
                with gr.Row():
                    export_fmt = gr.Dropdown(label="Export Format", choices=["json", "csv"], value="json", scale=2)
                    gr.HTML("<small style='color:#94a3b8;'>Download via: <a href='http://localhost:8000/api/v1/audit/export?format=csv' target='_blank' style='color:#d4af37;'>audit/export</a></small>")

                def load_stats():
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import AuditLog
                        from sqlalchemy import func
                        db = SessionLocal()
                        action_counts = (
                            db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
                            .group_by(AuditLog.action)
                            .order_by(func.count(AuditLog.id).desc())
                            .limit(10).all()
                        )
                        user_counts = (
                            db.query(AuditLog.user_id, func.count(AuditLog.id).label("count"))
                            .filter(AuditLog.user_id.isnot(None))
                            .group_by(AuditLog.user_id)
                            .order_by(func.count(AuditLog.id).desc())
                            .limit(5).all()
                        )

                        return {
                            "top_actions": [{"action": a, "count": c} for a, c in action_counts],
                            "top_users":   [{"user_id": u, "count": c} for u, c in user_counts]
                        }
                    except Exception as e:
                        return {"error": str(e)}

                stats_btn.click(load_stats, outputs=[stats_result])

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
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import User, Project, Scan
                        from sqlalchemy import func
                        db = SessionLocal()
                        rows = db.query(User.email, func.count(Scan.id).label("scans")).join(
                            Project, Project.owner_id == User.id
                        ).join(Scan, Scan.project_id == Project.id).group_by(User.email).order_by(
                            func.count(Scan.id).desc()).limit(10).all()

                        return [{"user": r[0], "total_scans": r[1]} for r in rows] or [{"message": "No data yet"}]
                    except Exception as e:
                        return {"error": str(e)}

                def load_health():
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Project, Scan
                        db = SessionLocal()
                        projects = db.query(Project).all()
                        result = []
                        for p in projects:
                            last_scan = db.query(Scan).filter(Scan.project_id == p.id).order_by(Scan.created_at.desc()).first()
                            health = (last_scan.result_summary or {}).get("health_score", "N/A") if last_scan else "No scans"
                            result.append({"project": p.name, "health": health, "last_scan": str(last_scan.created_at)[:16] if last_scan else "Never"})

                        return result or [{"message": "No projects yet"}]
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
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PluginConfig
                        db = SessionLocal()
                        plugins = db.query(PluginConfig).order_by(PluginConfig.created_at.desc()).all()
                        db.close()
                        if not plugins:
                            return [{"message": "Plugin system ready — no plugins registered yet. Register one below."}]
                        return [{"id": p.id, "name": p.name, "type": p.type,
                                 "description": p.description,
                                 "enabled": p.is_active,
                                 "builtin": p.is_builtin,
                                 "version": (p.config or {}).get("version", "N/A"),
                                 "created": str(p.created_at)[:16]} for p in plugins]
                    except Exception as e:
                        return [{"error": str(e)}]

                def register_plugin(name, ptype, version, desc):
                    if not name:
                        return "Enter a plugin name."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PluginConfig
                        db = SessionLocal()
                        # Check if plugin with same name already exists
                        existing = db.query(PluginConfig).filter(PluginConfig.name == name.strip()).first()
                        if existing:
                            db.close()
                            return f"Plugin '{name}' already exists (ID: {existing.id[:8]}...)."
                        plugin = PluginConfig(
                            name=name.strip(),
                            type=ptype or "parser",
                            description=desc or "",
                            config={"version": version or "1.0.0"},
                            is_builtin=False,
                            is_active=True,
                        )
                        db.add(plugin)
                        db.commit()
                        db.refresh(plugin)
                        pid = plugin.id
                        db.close()
                        return f"✅ Registered: {name} (ID: {pid[:8]}...)"
                    except Exception as e:
                        return f"Error: {e}"

                def toggle_plugin(pid, enabled):
                    if not pid:
                        return "Enter a Plugin ID."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PluginConfig
                        db = SessionLocal()
                        plugin = db.query(PluginConfig).filter(PluginConfig.id == pid.strip()).first()
                        if not plugin:
                            db.close()
                            return f"Plugin not found with ID: {pid.strip()}"
                        plugin.is_active = bool(enabled)
                        db.commit()
                        db.close()
                        return f"Plugin {'enabled' if enabled else 'disabled'}."
                    except Exception as e:
                        return f"Error: {e}"

                def delete_plugin(pid):
                    if not pid:
                        return "Enter a Plugin ID."
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import PluginConfig
                        db = SessionLocal()
                        plugin = db.query(PluginConfig).filter(PluginConfig.id == pid.strip()).first()
                        if not plugin:
                            db.close()
                            return f"Plugin not found with ID: {pid.strip()}"
                        db.delete(plugin)
                        db.commit()
                        db.close()
                        return f"Plugin '{plugin.name}' removed."
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
                        cicd_proj = gr.Dropdown(label="Select Project", choices=_load_project_choices(), scale=3, interactive=True)
                        cicd_threshold = gr.Slider(label="Min Health % (gate)", minimum=0, maximum=100, value=80, scale=2)
                        cicd_refresh = gr.Button("🔄", elem_classes=["glass-btn"], scale=0, min_width=40)
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
                    if not pid:
                        return "-", "-", {"error": "Enter a Project ID"}
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Scan
                        db = SessionLocal()
                        last_scan = db.query(Scan).filter(Scan.project_id == pid.strip()).order_by(Scan.created_at.desc()).first()

                        if not last_scan or not last_scan.result_summary:
                            return "-", "-", {"error": "No scans found for this project. Run an analysis first."}
                        health = last_scan.result_summary.get("health_score", 0)
                        passed = health >= int(threshold)
                        status_color = "#30d158" if passed else "#ef4444"
                        status_text = "✅ PASS" if passed else "❌ FAIL"
                        h_s = f"<div class='metric-value' style='color:{status_color}'>{status_text}</div><div class='metric-label'>Gate Status</div>"
                        h_h = f"<div class='metric-value'>{health}%</div><div class='metric-label'>Health Score</div>"
                        report = {"gate_passed": passed, "current_health": health, "threshold": int(threshold),
                                  "scan_id": last_scan.id, "scan_date": str(last_scan.created_at), "summary": last_scan.result_summary}
                        return h_s, h_h, report
                    except Exception as e:
                        return "-", "-", {"error": str(e)}

                cicd_refresh.click(lambda: gr.update(choices=_load_project_choices()), outputs=[cicd_proj])
                cicd_btn.click(
                    lambda: gr.update(interactive=False, value="\u23f3 Checking..."), outputs=[cicd_btn]
                ).then(
                    run_gate, inputs=[cicd_proj, cicd_threshold],
                    outputs=[gate_status_html, gate_health_html, cicd_result],
                    concurrency_limit=1,
                ).then(
                    lambda: gr.update(interactive=True, value="Run Gate Check"), outputs=[cicd_btn]
                )

            # ─── Tab 7: Analysis (Admin also runs scans) ──────────────────────
            with gr.TabItem("⚡ Analysis"):
                with gr.Row():
                    with gr.Column(scale=1, elem_classes=["frosted-sidebar"]):
                        gr.HTML("<div class='sidebar-title'>All Projects</div>")
                        project_selector = gr.Dropdown(label="", choices=[], interactive=True)
                        with gr.Row():
                            new_proj_code = gr.Textbox(label="Project Code", placeholder="e.g. PROJ_1, P1, 101")
                            new_proj_name = gr.Textbox(label="Project Name", placeholder="e.g. My App v2")
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

                def create_project(code, name, uid):
                    if not code or not name:
                        return gr.update(), "Both Project Code and Name are required."
                    code = code.strip().upper()  # always uppercase
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Project, ProjectMember
                        db = SessionLocal()
                        # Check code uniqueness
                        existing = db.query(Project).filter(Project.project_code == code).first()
                        if existing:
                            db.close()
                            return gr.update(), f"Project code '{code}' already exists. Choose a unique code."
                        p = Project(project_code=code, name=name, owner_id=uid, description="")
                        db.add(p)
                        db.flush()  # get p.id before creating member
                        # Auto-assign creator as write member
                        member = ProjectMember(user_id=uid, project_id=p.id, access_level="write", assigned_by=uid)
                        db.add(member)
                        db.commit()
                        db.refresh(p)
                        # Reload ALL projects for admin
                        projs = db.query(Project).order_by(Project.created_at.desc()).all()
                        choices = [
                            (f"{pr.project_code or pr.id[:8]} \u2014 {pr.name}", pr.id)
                            for pr in projs
                        ]
                        db.close()
                        return gr.update(choices=choices, value=p.id), f"\u2705 Created: {code} \u2014 {name}"
                    except Exception as e:
                        return gr.update(), f"Error: {e}"

                def run_and_update(pid, config, source, use_ai):
                    res = run_analysis(config, source, use_ai)
                    m_f, m_c, m_d, m_e, m_h = res[0], res[1], res[2], res[3], res[4]

                    # ── Persist scan to DB so CI/CD Gate, Reports, etc. can find it ──
                    if pid:
                        try:
                            from flagguard.core.db import SessionLocal
                            from flagguard.core.models.tables import Scan
                            db = SessionLocal()
                            health_int = int(m_h.replace('%', '')) if isinstance(m_h, str) else 0
                            scan = Scan(
                                project_id=pid,
                                triggered_by='manual',
                                status='completed',
                                result_summary={
                                    'flag_count': m_f,
                                    'conflict_count': m_c + m_d,
                                    'enabled_count': m_e,
                                    'health_score': health_int,
                                },
                            )
                            db.add(scan); db.commit()
                        except Exception:
                            pass  # Don't break analysis if DB save fails

                    h_f = f"<div class='metric-value'>{m_f}</div><div class='metric-label'>Flags</div>"
                    h_a = f"<div class='metric-value'>{m_e}</div><div class='metric-label'>Active</div>"
                    h_c = f"<div class='metric-value'>{m_c+m_d}</div><div class='metric-label'>Conflicts</div>"
                    h_h = f"<div class='metric-value'>{m_h}</div><div class='metric-label'>Health</div>"
                    return h_f, h_a, h_c, h_h, res[5], res[6], res[7], res[8], res[9]

                create_proj_btn.click(create_project, inputs=[new_proj_code, new_proj_name, user_state], outputs=[project_selector, proj_msg])
                analyze_btn.click(
                    lambda: gr.update(interactive=False, value="\u23f3 Analysing..."), outputs=[analyze_btn]
                ).then(
                    run_and_update, inputs=[project_selector, file_input, source_input, use_llm],
                    outputs=[val_flags, val_active, val_conflicts, val_health, plot_status, plot_severity, report_md, graph_html, mermaid_code],
                    concurrency_limit=1,
                ).then(
                    lambda: gr.update(interactive=True, value="\u26a1 Run Analysis"), outputs=[analyze_btn]
                )

            # ─── Tab 8: Environments ──────────────────────────────────────────
            with gr.TabItem("🌍 Environments"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        env_proj = gr.Dropdown(label="Select Project", choices=_load_project_choices(), scale=2, interactive=True)
                        env_name_inp = gr.Textbox(label="Environment Name", placeholder="dev / staging / prod", scale=2)
                        env_refresh = gr.Button("🔄", elem_classes=["glass-btn"], scale=0, min_width=40)
                        env_btn = gr.Button("Create", elem_classes=["glass-btn"], scale=1)
                    env_overrides = gr.Textbox(label="Flag Overrides (JSON)", placeholder='{"dark_mode": true, "beta": false}', lines=3)
                    env_result = gr.JSON(label="Result")
                    gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-title'>Compare Environment Drift</div>")
                    with gr.Row():
                        drift_a = gr.Dropdown(label="Environment A", choices=_load_env_choices(), scale=1, interactive=True)
                        drift_b = gr.Dropdown(label="Environment B", choices=_load_env_choices(), scale=1, interactive=True)
                        drift_refresh = gr.Button("\U0001f504", elem_classes=["glass-btn"], scale=0, min_width=40)
                        drift_btn = gr.Button("Compare Drift", elem_classes=["glass-btn"], scale=1)
                    drift_result = gr.JSON(label="Drift Report")

                def create_env(pid, name, overrides):
                    import json as _json
                    if not pid or not name:
                        return {"error": "Project ID and Name required"}, gr.update(), gr.update()
                    try:
                        from flagguard.core.db import SessionLocal
                        from flagguard.core.models.tables import Environment, Project
                        try:
                            ovr = _json.loads(overrides) if overrides and overrides.strip() else {}
                            if not isinstance(ovr, dict):
                                return {"error": "Flag Overrides must be a JSON object like {\"key\": true}"}, gr.update(), gr.update()
                        except _json.JSONDecodeError:
                            return {"error": "❌ Flag Overrides must be valid JSON (e.g. {\"dark_mode\": true, \"beta\": false}). Leave empty for no overrides."}, gr.update(), gr.update()
                        db = SessionLocal()
                        proj = db.query(Project).filter(Project.id == pid.strip()).first()
                        if not proj:
                            return {"error": f"Project not found with ID '{pid.strip()}'. First create a project in the Analysis tab."}, gr.update(), gr.update()
                        existing = db.query(Environment).filter(Environment.project_id == pid.strip(), Environment.name == name).first()
                        if existing:
                            return {"error": f"Environment '{name}' already exists for this project"}, gr.update(), gr.update()
                        env = Environment(name=name, project_id=pid.strip(), flag_overrides=ovr)
                        db.add(env); db.commit(); db.refresh(env)
                        result = {"status": "✅ Created!", "id": env.id, "name": env.name, "project_id": env.project_id, "flag_overrides": env.flag_overrides}

                        return result, gr.update(choices=_load_env_choices()), gr.update(choices=_load_env_choices())
                    except Exception as e:
                        return {"error": str(e)}, gr.update(), gr.update()

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

                env_refresh.click(lambda: gr.update(choices=_load_project_choices()), outputs=[env_proj])
                env_btn.click(
                    lambda: gr.update(interactive=False, value="\u23f3 Creating..."), outputs=[env_btn]
                ).then(
                    create_env, inputs=[env_proj, env_name_inp, env_overrides],
                    outputs=[env_result, drift_a, drift_b],
                    concurrency_limit=1,
                ).then(
                    lambda: gr.update(interactive=True, value="Create"), outputs=[env_btn]
                )
                drift_refresh.click(lambda: (gr.update(choices=_load_env_choices()), gr.update(choices=_load_env_choices())), outputs=[drift_a, drift_b])
                drift_btn.click(compare_drift, inputs=[drift_a, drift_b], outputs=[drift_result])

            # ─── Tab 9: Reports ───────────────────────────────────────────────
            with gr.TabItem("📑 Reports"):
                with gr.Group(elem_classes=["glass-card"]):
                    with gr.Row():
                        rep_proj = gr.Dropdown(label="Select Project", choices=_load_project_choices(), scale=3, interactive=True)
                        rep_fmt = gr.Dropdown(label="Format", choices=["json","csv","markdown"], value="json", scale=1)
                        rep_refresh = gr.Button("🔄", elem_classes=["glass-btn"], scale=0, min_width=40)
                        rep_btn = gr.Button("Generate", elem_classes=["glass-btn"], scale=1)
                    rep_result = gr.JSON(label="Report")
                    exec_proj = gr.Dropdown(label="Select Project (Executive Summary)", choices=_load_project_choices(), interactive=True)
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

                rep_refresh.click(lambda: (gr.update(choices=_load_project_choices()), gr.update(choices=_load_project_choices())),
                                  outputs=[rep_proj, exec_proj])
                rep_btn.click(
                    lambda: gr.update(interactive=False, value="\u23f3 Generating..."), outputs=[rep_btn]
                ).then(
                    gen_report, inputs=[rep_proj, rep_fmt], outputs=[rep_result],
                    concurrency_limit=1,
                ).then(
                    lambda: gr.update(interactive=True, value="Generate"), outputs=[rep_btn]
                )
                exec_btn.click(
                    lambda: gr.update(interactive=False, value="\u23f3 Summarising..."), outputs=[exec_btn]
                ).then(
                    exec_summary, inputs=[exec_proj], outputs=[exec_result],
                    concurrency_limit=1,
                ).then(
                    lambda: gr.update(interactive=True, value="Executive Summary"), outputs=[exec_btn]
                )

            # ─── Tab 10: IaC Scan ─────────────────────────────────────────────
            with gr.TabItem("🏗️ IaC Scan"):
                with gr.Group(elem_classes=["glass-card"]):
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
                        # Simple IaC flag detection — scan for feature flag patterns
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
                            return "Current password wrong."
                        u.hashed_password = get_password_hash(new)
                        db.commit()
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
                from flagguard.core.models.tables import Project, User
                db = SessionLocal()
                projs = db.query(Project).order_by(Project.created_at.desc()).all()
                # Show project name + owner email for admin context
                user_map = {u.id: u.email for u in db.query(User).all()}

                choices = [(f"{p.name}  [{user_map.get(p.owner_id, p.owner_id[:8])}]", p.id) for p in projs]
                return gr.update(choices=choices, value=projs[0].id if projs else None)
            except Exception as e:
                return gr.update(choices=[], value=None)

        def _refresh_all_dropdowns(uid):
            """On login, refresh ALL project dropdowns across tabs."""
            proj_update = refresh_all_projects(uid)
            choices = _load_project_choices()
            dd = gr.update(choices=choices, value=choices[0][1] if choices else None)
            env_choices = _load_env_choices()
            dd_env = gr.update(choices=env_choices, value=env_choices[0][1] if env_choices else None)
            return proj_update, dd, dd, dd, dd, dd_env, dd_env

        user_state.change(_refresh_all_dropdowns, inputs=[user_state],
                          outputs=[project_selector, cicd_proj, env_proj, rep_proj, exec_proj, drift_a, drift_b])

        # ════════════════════════════════════════════════════════════════════
        # DSAR: Data Rights + Admin Deletion Requests
        # ════════════════════════════════════════════════════════════════════
        gr.HTML("<div style='margin:30px 0 10px;'></div>")
        with gr.Group(elem_classes=["glass-card"]):
            gr.HTML("""
            <div style='margin-bottom:16px;'>
                <div class='sidebar-title'>🔐 Data Rights & DSAR Management</div>
                <p style='color:#94a3b8; font-size:0.85rem; margin:0;'>
                    GDPR Art.15-17 / CCPA / India DPDP Act — Manage your own data and review user deletion requests.
                </p>
            </div>
            """)
            # Admin's own data rights
            with gr.Row():
                adm_export_btn = gr.Button("📥 Export My Data", elem_classes=["glass-btn"], size="sm")
                adm_delete_btn = gr.Button("🗑️ Request Account Deletion", elem_classes=["danger-btn"], size="sm")
            adm_dsar_output = gr.JSON(label="Your Data Export", visible=False)
            adm_dsar_msg = gr.HTML("")

            # Admin: Deletion request management
            gr.HTML("<hr style='border:none; border-top:1px solid rgba(212,175,55,0.1); margin:20px 0;'/>")
            gr.HTML("<div class='sidebar-title'>⚖️ Pending Deletion Requests (Admin Review)</div>")
            adm_del_refresh = gr.Button("↻ Refresh Requests", elem_classes=["glass-btn"], size="sm")
            adm_del_table = gr.JSON(label="Pending Deletion Requests")
            with gr.Row():
                adm_del_id = gr.Textbox(label="Request ID", placeholder="Paste request ID to approve/reject", scale=3)
                adm_del_approve = gr.Button("✅ Approve", elem_classes=["success-btn"], size="sm", scale=1)
                adm_del_reject = gr.Button("❌ Reject", elem_classes=["danger-btn"], size="sm", scale=1)
            adm_del_msg = gr.HTML("")

        def adm_export_my_data(uid):
            if not uid:
                return gr.update(visible=False), "<div style='color:#ef4444;'>Not logged in.</div>"
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import User, Project, AuditLog, ProjectMember
                db = SessionLocal()
                user = db.query(User).filter(User.id == uid).first()
                if not user:
                    return gr.update(visible=False), "<div style='color:#ef4444;'>User not found.</div>"
                projects = db.query(Project).filter(Project.owner_id == uid).all()
                memberships = db.query(ProjectMember).filter(ProjectMember.user_id == uid).all()
                audit_count = db.query(AuditLog).filter(AuditLog.user_id == uid).count()
                db.close()
                export = {
                    "export_date": str(__import__("datetime").datetime.utcnow()),
                    "user": {"email": user.email, "full_name": user.full_name, "role": user.role, "created_at": str(user.created_at)},
                    "projects_owned": [{"id": p.id, "code": p.project_code, "name": p.name} for p in projects],
                    "project_memberships": [{"project_id": m.project_id, "access": m.access_level} for m in memberships],
                    "audit_entries": audit_count,
                }
                return gr.update(visible=True, value=export), "<div style='color:#30d158;'>✅ Data exported.</div>"
            except Exception as e:
                return gr.update(visible=False), f"<div style='color:#ef4444;'>Error: {e}</div>"

        def adm_request_deletion(uid):
            if not uid:
                return "<div style='color:#ef4444;'>Not logged in.</div>"
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import DeletionRequest
                db = SessionLocal()
                existing = db.query(DeletionRequest).filter(DeletionRequest.user_id == uid, DeletionRequest.status == "pending").first()
                if existing:
                    return "<div style='color:#f59e0b;'>⏳ Pending request already exists.</div>"
                db.add(DeletionRequest(user_id=uid, reason="Admin self-deletion via DSAR"))
                db.commit(); db.close()
                return "<div style='color:#f59e0b;'>⏳ Deletion request submitted.</div>"
            except Exception as e:
                return f"<div style='color:#ef4444;'>Error: {e}</div>"

        def load_deletion_requests():
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import DeletionRequest, User
                db = SessionLocal()
                reqs = db.query(DeletionRequest).filter(DeletionRequest.status == "pending").all()
                user_map = {u.id: u.email for u in db.query(User).all()}
                data = [{"id": r.id, "user": user_map.get(r.user_id, r.user_id[:8]),
                         "reason": r.reason, "requested": str(r.requested_at)} for r in reqs]
                db.close()
                return data
            except Exception:
                return []

        def handle_deletion(req_id, action, admin_uid):
            if not req_id:
                return "<div style='color:#ef4444;'>Please enter a Request ID.</div>", []
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import DeletionRequest, User, AuditLog
                from datetime import datetime as dt
                db = SessionLocal()
                req = db.query(DeletionRequest).filter(DeletionRequest.id == req_id).first()
                if not req:
                    return "<div style='color:#ef4444;'>Request not found.</div>", load_deletion_requests()
                req.status = action
                req.reviewed_at = dt.utcnow()
                req.reviewed_by = admin_uid
                if action == "approved":
                    # Soft-delete: deactivate user account
                    user = db.query(User).filter(User.id == req.user_id).first()
                    if user:
                        user.is_active = False
                    # Log the action
                    db.add(AuditLog(user_id=admin_uid, action="delete_user", resource_type="user",
                                    resource_id=req.user_id, details={"reason": "DSAR deletion approved"}))
                db.commit(); db.close()
                status_icon = "✅" if action == "approved" else "❌"
                return f"<div style='color:#30d158;'>{status_icon} Request {action}.</div>", load_deletion_requests()
            except Exception as e:
                return f"<div style='color:#ef4444;'>Error: {e}</div>", load_deletion_requests()

        adm_export_btn.click(adm_export_my_data, inputs=[user_state], outputs=[adm_dsar_output, adm_dsar_msg])
        adm_delete_btn.click(adm_request_deletion, inputs=[user_state], outputs=[adm_dsar_msg])
        adm_del_refresh.click(load_deletion_requests, outputs=[adm_del_table])
        adm_del_approve.click(lambda rid, uid: handle_deletion(rid, "approved", uid), inputs=[adm_del_id, user_state], outputs=[adm_del_msg, adm_del_table])
        adm_del_reject.click(lambda rid, uid: handle_deletion(rid, "rejected", uid), inputs=[adm_del_id, user_state], outputs=[adm_del_msg, adm_del_table])

    return dashboard, logout_btn

