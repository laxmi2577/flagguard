"""FlagGuard — Role-Based UI Router.

Handles login, signup request, and routes users to the correct
role-specific dashboard (viewer / analyst / admin).
"""

import gradio as gr
from flagguard.ui.styles import LIQUID_GLASS_CSS, get_theme
from flagguard.ui.tabs.viewer_dashboard  import create_viewer_dashboard
from flagguard.ui.tabs.analyst_dashboard import create_analyst_dashboard
from flagguard.ui.tabs.admin_dashboard   import create_admin_dashboard

def create_app():
    theme = get_theme()

    with gr.Blocks(title="FlagGuard", theme=theme, css=LIQUID_GLASS_CSS) as app:

        # ── Shared state ────────────────────────────────────────────────────
        user_id   = gr.State("")
        user_role = gr.State("viewer")

        # ════════════════════════════════════════════════════════════════════
        # LOGIN + SIGNUP VIEW
        # ════════════════════════════════════════════════════════════════════
        with gr.Group(visible=True, elem_classes=["login-bg"]) as login_view:
            with gr.Row():
                gr.Column(scale=1)
                with gr.Column(scale=1):
                    gr.HTML("<div style='height:8vh;'></div>")

                    # ── Mode toggle (Login / Sign Up) ────────────────────────
                    with gr.Row():
                        mode_login_btn  = gr.Button("Sign In",  elem_classes=["glass-btn"])
                        mode_signup_btn = gr.Button("Request Access", elem_classes=["glass-btn"])

                    # ── LOGIN CARD ───────────────────────────────────────────
                    with gr.Group(visible=True, elem_classes=["glass-card","shimmer-border"]) as login_card:
                        gr.HTML("""
                        <div style='text-align:center;margin-bottom:28px;'>
                            <div class='login-logo'>🛡</div>
                            <div class='login-title'>FlagGuard</div>
                            <div class='login-subtitle'>Enterprise Feature Flag Intelligence</div>
                        </div>
                        <div class='sidebar-title' style='text-align:center;margin-bottom:16px;'>Sign In</div>""")

                        email_input    = gr.Textbox(placeholder="Email address", show_label=False, container=False)
                        password_input = gr.Textbox(placeholder="Password", type="password", show_label=False, container=False)
                        login_btn      = gr.Button("→ Sign In", elem_classes=["glass-btn"])
                        login_msg      = gr.HTML("")

                        gr.HTML("""
                        <div style='text-align:center;margin-top:16px;font-size:0.8rem;color:#94a3b8;'>
                            Don't have access? Click <b>Request Access</b> above to apply.
                        </div>""")

                    # ── SIGNUP CARD ──────────────────────────────────────────
                    with gr.Group(visible=False, elem_classes=["glass-card","shimmer-border"]) as signup_card:
                        gr.HTML("""
                        <div style='text-align:center;margin-bottom:28px;'>
                            <div class='login-logo'>📝</div>
                            <div class='login-title'>Request Access</div>
                            <div class='login-subtitle'>Admin will review your request</div>
                        </div>""")

                        su_name  = gr.Textbox(placeholder="Full Name", show_label=False, container=False)
                        su_email = gr.Textbox(placeholder="Email address", show_label=False, container=False)
                        su_pw    = gr.Textbox(placeholder="Password", type="password", show_label=False, container=False)
                        su_pw2   = gr.Textbox(placeholder="Confirm Password", type="password", show_label=False, container=False)
                        su_role  = gr.Radio(
                            label="I need access as:",
                            choices=[("Viewer — Read-only access", "viewer"),
                                     ("Analyst — Can run scans & manage projects", "analyst")],
                            value="viewer"
                        )
                        su_reason = gr.Textbox(
                            placeholder="Briefly explain why you need access...",
                            lines=2, show_label=False, container=False
                        )
                        signup_btn = gr.Button("→ Submit Request", elem_classes=["glass-btn"])
                        signup_msg = gr.HTML("")

                        # Check existing request status
                        gr.HTML("<div style='margin:16px 0;border-top:1px solid rgba(212,175,55,0.1);'></div>")
                        gr.HTML("<div class='sidebar-title' style='text-align:center;'>Check Your Request Status</div>")
                        check_email = gr.Textbox(placeholder="Enter your email to check status", show_label=False, container=False)
                        check_btn   = gr.Button("Check Status", elem_classes=["glass-btn"], size="sm")
                        check_msg   = gr.HTML("")

                gr.Column(scale=1)

        # ════════════════════════════════════════════════════════════════════
        # ROLE DASHBOARDS (hidden until login)
        # ════════════════════════════════════════════════════════════════════
        viewer_dash,  viewer_logout  = create_viewer_dashboard(app,  user_id)[:2]
        analyst_dash, analyst_logout = create_analyst_dashboard(app, user_id)[:2]
        admin_dash,   admin_logout   = create_admin_dashboard(app,   user_id)[:2]

        # ════════════════════════════════════════════════════════════════════
        # EVENT HANDLERS
        # ════════════════════════════════════════════════════════════════════

        # Toggle between login and signup card
        mode_login_btn.click(
            lambda: (gr.update(visible=True), gr.update(visible=False)),
            outputs=[login_card, signup_card]
        )
        mode_signup_btn.click(
            lambda: (gr.update(visible=False), gr.update(visible=True)),
            outputs=[login_card, signup_card]
        )

        # ── Login ────────────────────────────────────────────────────────────
        def perform_login(email, password):
            from flagguard.core.db import SessionLocal
            from flagguard.core.models.tables import User
            from flagguard.auth.utils import verify_password

            def hide_all():
                return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))

            try:
                db = SessionLocal()
                user = db.query(User).filter(User.email == email).first()

                if not user or not verify_password(password, user.hashed_password):
                    # Check if pending
                    db2 = SessionLocal()
                    from flagguard.core.models.tables import PendingUser
                    pending = db2.query(PendingUser).filter(PendingUser.email == email).first()
                    db2.close()
                    if pending and pending.status == "pending":
                        msg = "<div style='color:#f59e0b;text-align:center;padding:8px;'>⏳ Your request is pending admin approval.</div>"
                    elif pending and pending.status == "rejected":
                        msg = "<div style='color:#ef4444;text-align:center;padding:8px;'>❌ Your request was rejected. Contact admin.</div>"
                    else:
                        msg = "<div style='color:#ef4444;text-align:center;padding:8px;'>❌ Invalid email or password.</div>"
                    return (gr.update(), "viewer", msg,
                            gr.update(), *hide_all())

                if not user.is_active:
                    return (gr.update(), "viewer",
                            "<div style='color:#ef4444;text-align:center;padding:8px;'>❌ Account is deactivated. Contact admin.</div>",
                            gr.update(), *hide_all())

                role = getattr(user, "role", "viewer") or "viewer"

                # Show the right dashboard
                show_viewer  = role == "viewer"
                show_analyst = role == "analyst"
                show_admin   = role == "admin"

                return (
                    user.id,  role, "",
                    gr.update(visible=False),           # login_view
                    gr.update(visible=show_viewer),     # viewer_dash
                    gr.update(visible=show_analyst),    # analyst_dash
                    gr.update(visible=show_admin),      # admin_dash
                )
            except Exception as e:
                return (gr.update(), "viewer",
                        f"<div style='color:#ef4444;'>⚠️ Error: {e}</div>",
                        gr.update(), *hide_all())

        login_btn.click(
            perform_login,
            inputs=[email_input, password_input],
            outputs=[user_id, user_role, login_msg, login_view,
                     viewer_dash, analyst_dash, admin_dash]
        )

        # ── Signup Request ───────────────────────────────────────────────────
        def perform_signup(name, email, pw, pw2, role, reason):
            if not name or not email or not pw:
                return "<div style='color:#ef4444;'>All fields required.</div>"
            if pw != pw2:
                return "<div style='color:#ef4444;'>Passwords do not match.</div>"
            from flagguard.auth.utils import validate_password
            pw_errors = validate_password(pw)
            if pw_errors:
                return "<div style='color:#ef4444;'>" + "<br>".join(pw_errors) + "</div>"
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import User, PendingUser
                from flagguard.auth.utils import get_password_hash
                db = SessionLocal()
                if db.query(User).filter(User.email == email).first():

                    return "<div style='color:#ef4444;'>Email already has an active account.</div>"
                existing = db.query(PendingUser).filter(PendingUser.email == email).first()
                if existing and existing.status == "pending":

                    return "<div style='color:#f59e0b;'>⏳ A pending request already exists for this email.</div>"
                pending = PendingUser(
                    full_name=name, email=email,
                    hashed_password=get_password_hash(pw),
                    requested_role=role, reason=reason or ""
                )
                db.add(pending); db.commit()
                return """<div style='background:rgba(48,209,88,0.1);border:1px solid rgba(48,209,88,0.3);
                                     border-radius:8px;padding:12px;text-align:center;color:#30d158;'>
                    ✅ Request submitted!<br>
                    <small>An admin will review your request. You'll be able to log in once approved.</small>
                </div>"""
            except Exception as e:
                return f"<div style='color:#ef4444;'>Error: {e}</div>"

        signup_btn.click(
            perform_signup,
            inputs=[su_name, su_email, su_pw, su_pw2, su_role, su_reason],
            outputs=[signup_msg]
        )

        # ── Check Request Status ─────────────────────────────────────────────
        def check_request_status(email):
            if not email:
                return ""
            try:
                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import PendingUser
                db = SessionLocal()
                p = db.query(PendingUser).filter(PendingUser.email == email).first()

                if not p:
                    return "<div style='color:#94a3b8;'>No request found for this email.</div>"
                colors = {"pending": "#f59e0b", "approved": "#30d158", "rejected": "#ef4444"}
                icons  = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
                color  = colors.get(p.status, "#94a3b8")
                icon   = icons.get(p.status, "")
                return f"<div style='color:{color};text-align:center;padding:8px;'>{icon} Status: <b>{p.status.upper()}</b></div>"
            except Exception as e:
                return f"<div style='color:#ef4444;'>Error: {e}</div>"

        check_btn.click(check_request_status, inputs=[check_email], outputs=[check_msg])

        # ── Logout (all 3 dashboards share same logic) ────────────────────────
        def do_logout():
            return ("",          # clear user_id state
                    "viewer",    # reset user_role state
                    gr.update(visible=True),   # login_view
                    gr.update(visible=False),   # viewer_dash
                    gr.update(visible=False),   # analyst_dash
                    gr.update(visible=False))   # admin_dash

        for btn in [viewer_logout, analyst_logout, admin_logout]:
            btn.click(do_logout, outputs=[user_id, user_role, login_view, viewer_dash, analyst_dash, admin_dash])

    return app

def launch():
    import os
    import threading
    import time
    import uvicorn

    # Guard against Windows cp1252 console encoding issue with emoji
    if os.name == "nt":
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # ── Start FastAPI API server on port 8000 in background ──────────────
    def run_api():
        """Run the FastAPI API server (all REST endpoints)."""
        from flagguard.api.server import app as api_app
        uvicorn.run(api_app, host="0.0.0.0", port=8000, log_level="warning")

    api_thread = threading.Thread(target=run_api, daemon=True, name="api-server")
    api_thread.start()
    print("[OK] API server starting on http://localhost:8000 ...")
    time.sleep(1)  # Give API server a moment to bind

    # ── Start Gradio UI on port 7860 ────────────────────────────────────
    app = create_app()
    print("[OK] Gradio UI starting on http://localhost:7860 ...")
    app.launch(show_error=True, allowed_paths=["."])

if __name__ == "__main__":
    launch()

