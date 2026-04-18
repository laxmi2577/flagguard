"""FlagGuard — Role-Based UI Router.

Handles login, signup request, and routes users to the correct
role-specific dashboard (viewer / analyst / admin).
"""

import gradio as gr

# ── FlagGuard SVG Logo (used on login, signup, browser favicon) ───────────────
# Shield + flag pennant + AI circuit dots. Gold/blue on dark.
FG_LOGO_SVG = """<svg viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:56px;height:56px;">
  <defs>
    <linearGradient id="lg-bg" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0f0f1a"/><stop offset="100%" stop-color="#1a1a2e"/>
    </linearGradient>
    <radialGradient id="lg-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#d4af37" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#d4af37" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="56" height="56" rx="14" fill="url(#lg-bg)"/>
  <rect width="56" height="56" rx="14" fill="url(#lg-glow)"/>
  <!-- Shield -->
  <path d="M28 7 L44 13 L44 30 C44 39 36.5 45.5 28 48 C19.5 45.5 12 39 12 30 L12 13 Z"
        fill="none" stroke="url(#lg-gold)" stroke-width="1.8" stroke-linejoin="round"/>
  <defs>
    <linearGradient id="lg-gold" x1="12" y1="7" x2="44" y2="48" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#d4af37"/>
    </linearGradient>
  </defs>
  <!-- Flag staff -->
  <line x1="22" y1="17" x2="22" y2="38" stroke="#d4af37" stroke-width="2" stroke-linecap="round"/>
  <!-- Flag pennant -->
  <path d="M22 17 L34 21.5 L22 26 Z" fill="#d4af37"/>
  <!-- AI circuit nodes -->
  <circle cx="28" cy="7" r="1.5" fill="#3b82f6" opacity="0.9"/>
  <circle cx="44" cy="13" r="1.5" fill="#3b82f6" opacity="0.9"/>
  <circle cx="44" cy="30" r="1.5" fill="#3b82f6" opacity="0.7"/>
  <circle cx="12" cy="13" r="1.5" fill="#3b82f6" opacity="0.9"/>
  <circle cx="12" cy="30" r="1.5" fill="#3b82f6" opacity="0.7"/>
  <circle cx="28" cy="48" r="1.5" fill="#3b82f6" opacity="0.6"/>
  <!-- AI circuit lines -->
  <line x1="28" y1="7" x2="22" y2="17" stroke="#3b82f6" stroke-width="0.5" opacity="0.4"/>
  <line x1="44" y1="13" x2="34" y2="21.5" stroke="#3b82f6" stroke-width="0.5" opacity="0.4"/>
  <line x1="12" y1="30" x2="22" y2="26" stroke="#3b82f6" stroke-width="0.5" opacity="0.35"/>
  <!-- Outer glow ring -->
  <circle cx="28" cy="28" r="26" stroke="#d4af37" stroke-width="0.4" opacity="0.15"/>
</svg>"""

from flagguard.ui.styles import LIQUID_GLASS_CSS, get_theme
from flagguard.ui.tabs.viewer_dashboard  import create_viewer_dashboard
from flagguard.ui.tabs.analyst_dashboard import create_analyst_dashboard
from flagguard.ui.tabs.admin_dashboard   import create_admin_dashboard

def create_app():
    theme = get_theme()

    # ======================================================================
    # Cookie consent + legal reader modals are handled by:
    #   1. /src/flagguard/static/fg-modals.js (creates overlays on body)
    #   2. ScriptInjectionMiddleware in server.py (injects <script> tag)
    #   3. /api/v1/legal/{key} endpoint (serves legal docs as HTML)
    # This completely bypasses Gradio's DOMPurify sanitization.
    # ======================================================================

    with gr.Blocks(title="FlagGuard · AI-Powered Flag Intelligence", theme=theme, css=LIQUID_GLASS_CSS) as app:
        # Shared State
        user_id       = gr.State("")
        user_role     = gr.State("viewer")
        session_token = gr.Textbox(visible=False, value="", elem_id="fg-session-token")

        # ====================================================================
        # LOGIN + SIGNUP VIEW
        # ====================================================================
        with gr.Group(visible=True, elem_classes=["login-bg"]) as login_view:
            with gr.Row():
                gr.Column(scale=1)
                with gr.Column(scale=1):
                    gr.HTML("<div style='height:8vh;'></div>")

                    # Mode Toggle (Login / Sign Up)
                    with gr.Row():
                        mode_login_btn  = gr.Button("Sign In",  elem_classes=["glass-btn"])
                        mode_signup_btn = gr.Button("Request Access", elem_classes=["glass-btn"])

                    # Login Card UI
                    with gr.Group(visible=True, elem_classes=["glass-card","shimmer-border"]) as login_card:
                        gr.HTML(f"""
                        <div style='text-align:center;margin-bottom:28px;'>
                            <div class='login-logo' style='display:flex;justify-content:center;margin-bottom:8px;'>{FG_LOGO_SVG}</div>
                            <div class='login-title'>FlagGuard</div>
                            <div class='login-subtitle'>AI-Powered Feature Flag Intelligence</div>
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

                    # Signup Card UI
                    with gr.Group(visible=False, elem_classes=["glass-card","shimmer-border"]) as signup_card:
                        gr.HTML(f"""
                        <div style='text-align:center;margin-bottom:28px;'>
                            <div class='login-logo' style='display:flex;justify-content:center;margin-bottom:8px;'>{FG_LOGO_SVG}</div>
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

        # ====================================================================
        # ROLE DASHBOARDS (hidden until login)
        # ====================================================================
        viewer_dash,  viewer_logout  = create_viewer_dashboard(app,  user_id)[:2]
        analyst_dash, analyst_logout = create_analyst_dashboard(app, user_id)[:2]
        admin_dash,   admin_logout   = create_admin_dashboard(app,   user_id)[:2]

        # ====================================================================
        # EVENT HANDLERS
        # ====================================================================

        # Toggle between login and signup card
        mode_login_btn.click(
            lambda: (gr.update(visible=True), gr.update(visible=False)),
            outputs=[login_card, signup_card]
        )
        mode_signup_btn.click(
            lambda: (gr.update(visible=False), gr.update(visible=True)),
            outputs=[login_card, signup_card]
        )

        # Login Handlers
        def perform_login(email, password):
            from flagguard.core.db import SessionLocal
            from flagguard.core.models.tables import User
            from flagguard.auth.utils import verify_password, create_access_token

            def hide_all():
                return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))

            try:
                db = SessionLocal()
                user = db.query(User).filter(User.email == email).first()

                if not user or not verify_password(password, user.hashed_password):
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
                    return (gr.update(), "viewer", msg, "",
                            gr.update(), *hide_all())

                if not user.is_active:
                    return (gr.update(), "viewer",
                            "<div style='color:#ef4444;text-align:center;padding:8px;'>❌ Account is deactivated. Contact admin.</div>",
                            "", gr.update(), *hide_all())

                role = getattr(user, "role", "viewer") or "viewer"

                # Generate JWT token for persistent session cookie
                token = create_access_token({"sub": user.id, "role": role})

                show_viewer  = role == "viewer"
                show_analyst = role == "analyst"
                show_admin   = role == "admin"

                return (
                    user.id, role, "", token,
                    gr.update(visible=False),
                    gr.update(visible=show_viewer),
                    gr.update(visible=show_analyst),
                    gr.update(visible=show_admin),
                )
            except Exception as e:
                return (gr.update(), "viewer",
                        f"<div style='color:#ef4444;'>⚠️ Error: {e}</div>",
                        "", gr.update(), *hide_all())

        login_btn.click(
            perform_login,
            inputs=[email_input, password_input],
            outputs=[user_id, user_role, login_msg, session_token,
                     login_view, viewer_dash, analyst_dash, admin_dash]
        ).then(
            fn=None, inputs=[session_token],
            js="(token) => { if(token) document.cookie='fg_session='+token+';path=/;max-age=3600;SameSite=Lax'; }"
        )

        # Signup Request Handlers
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

        # Check Request Status
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

        # Logout Handlers
        def do_logout():
            return ("",          # clear user_id state
                    "viewer",    # reset user_role state
                    gr.update(visible=True),   # login_view
                    gr.update(visible=False),   # viewer_dash
                    gr.update(visible=False),   # analyst_dash
                    gr.update(visible=False))   # admin_dash

        for btn in [viewer_logout, analyst_logout, admin_logout]:
            btn.click(do_logout, outputs=[user_id, user_role, login_view, viewer_dash, analyst_dash, admin_dash]).then(
                fn=None,
                js="() => { document.cookie='fg_session=;path=/;expires=Thu,01 Jan 1970 00:00:00 GMT'; }"
            )

        # Session Restore via JWT Cookie
        def _restore_session(request: gr.Request):
            """Auto-restore user session from JWT cookie on page load."""
            try:
                cookie_val = request.cookies.get("fg_session", "")
                print(f"[SESSION] Cookie present: {bool(cookie_val)}, length: {len(cookie_val)}")
                if not cookie_val:
                    print("[SESSION] No cookie found — showing login")
                    return _no_session()

                from flagguard.auth.utils import verify_token
                payload = verify_token(cookie_val)
                if not payload:
                    print("[SESSION] Token verification FAILED — expired or invalid")
                    return _no_session()

                uid  = payload.get("sub", "")
                role = payload.get("role", "viewer")
                print(f"[SESSION] Token valid — uid={uid[:8]}..., role={role}")

                from flagguard.core.db import SessionLocal
                from flagguard.core.models.tables import User
                db = SessionLocal()
                user = db.query(User).filter(User.id == uid).first()
                db.close()

                if not user or not user.is_active:
                    print("[SESSION] User not found or inactive")
                    return _no_session()

                print(f"[SESSION] ✅ Restored session for {user.email} ({role})")
                return (
                    user.id, role,
                    gr.update(visible=False),
                    gr.update(visible=(role == "viewer")),
                    gr.update(visible=(role == "analyst")),
                    gr.update(visible=(role == "admin")),
                )
            except Exception as e:
                print(f"[SESSION] Exception: {e}")
                return _no_session()

        def _no_session():
            """Default state — show login screen."""
            return ("", "viewer",
                    gr.update(visible=True),
                    gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))

        app.load(
            _restore_session,
            outputs=[user_id, user_role, login_view, viewer_dash, analyst_dash, admin_dash]
        )

        # ════════════════════════════════════════════════════════════════════
        # GLOBAL LEGAL FOOTER (WCAG 2.2 compliant contrast)
        # Footer links use data-legal attributes — event handling is in
        # fg-modals.js which is injected by ScriptInjectionMiddleware.
        # ════════════════════════════════════════════════════════════════════
        gr.HTML("""
        <footer style='text-align:center; padding:20px 20px 16px; font-size:0.8rem; color:#94a3b8; border-top:1px solid #334155; margin-top:40px; width:100%;' role="contentinfo" aria-label="Global Legal Footer">
            <div style='display:flex; justify-content:center; gap:16px; margin-bottom:8px; flex-wrap:wrap;'>
                <a href="#" data-legal="privacy" style='color:#cbd5e1; text-decoration:none;' aria-label="Privacy Policy">Privacy Policy</a>
                <a href="#" data-legal="terms" style='color:#cbd5e1; text-decoration:none;' aria-label="Terms of Service">Terms of Service</a>
                <a href="#" data-legal="aup" style='color:#cbd5e1; text-decoration:none;' aria-label="Acceptable Use Policy">Acceptable Use</a>
                <a href="#" data-legal="accessibility" style='color:#cbd5e1; text-decoration:none;' aria-label="Accessibility Statement">Accessibility</a>
                <a href="#" data-legal="ai" style='color:#cbd5e1; text-decoration:none;' aria-label="AI Transparency">AI Transparency</a>
                <a href="#" data-legal="data" style='color:#cbd5e1; text-decoration:none;' aria-label="Data Inventory">Data Inventory</a>
            </div>
            <div style='margin-bottom:6px;'>&copy; 2026 FlagGuard Enterprise Intelligence. Built for SOC2/ISO27001 Environments.</div>
            <div style='font-size:0.7rem; color:#64748b;'>Grievance Officer: Laxmiranjan Sahu &middot; <a href="mailto:laxmiranjan444@gmail.com" style="color:#94a3b8;">laxmiranjan444@gmail.com</a></div>
        </footer>
        """)

    return app

def launch():
    import os
    import uvicorn

    # Guard against Windows cp1252 console encoding issue with emoji
    if os.name == "nt":
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Import the FastAPI API app
    from flagguard.api.server import app as api_app

    # Create the Gradio UI
    gradio_app = create_app()

    # Mount Gradio onto FastAPI (Single Server Shared Cookies)
    gr.mount_gradio_app(api_app, gradio_app, path="/")

    port = int(os.environ.get("PORT", 8000))
    print(f"[OK] FlagGuard starting on http://localhost:{port}")
    print(f"[OK] Dashboard \u2192 http://localhost:{port}/")
    print(f"[OK] API Docs  \u2192 http://localhost:{port}/docs")
    
    # Ensure database is generated after all imports are safely resolved
    try:
        from flagguard.core.db import init_db
        print("[OK] Running database migrations...")
        init_db()
    except Exception as e:
        print(f"[ERROR] Database init failed: {e}")

    uvicorn.run(api_app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    launch()
