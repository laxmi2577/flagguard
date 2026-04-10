"""Shared header component for all role dashboards.

Provides:
- Brand logo + status dot
- Dark / Light mode toggle (Feature D)
- Notification bell with unread count (Feature A) — loads real data from DB
- Role badge
- Sign Out button
"""

import gradio as gr

# JS injected once to manage dark/light mode via body class
DARK_LIGHT_JS = """
<script>
(function() {
    // Restore saved preference
    var pref = localStorage.getItem('fg_theme') || 'dark';
    if (pref === 'light') document.body.classList.add('light-mode');

    // Global toggle function called by Gradio button js=
    window.fgToggleTheme = function() {
        var isLight = document.body.classList.toggle('light-mode');
        localStorage.setItem('fg_theme', isLight ? 'light' : 'dark');
        // Update ALL toggle buttons across dashboards
        var btns = document.querySelectorAll('.theme-toggle-btn');
        btns.forEach(function(btn) {
            // Gradio buttons have inner span elements
            var sp = btn.querySelector('span') || btn;
            sp.textContent = isLight ? '\\u2600\\uFE0F Light' : '\\uD83C\\uDF19 Dark';
        });
    };
})();
</script>
"""

def build_header_html(role: str, notif_count: int = 0, notifications: list = None) -> str:
    """Build the full header HTML with brand, notifications, theme toggle and role badge."""
    badge_class = f"badge-{role}"
    role_label  = role.upper()
    uid = f"notif-{role}"  # unique ID per role to avoid BUG-18

    notif_count_label = str(notif_count) if notif_count <= 9 else "9+"
    notif_count_html  = (
        f"<span style='position:absolute;top:-4px;right:-4px;background:#ef4444;color:#fff;"
        f"border-radius:50%;width:16px;height:16px;font-size:0.6rem;font-weight:700;"
        f"display:flex;align-items:center;justify-content:center;'>{notif_count_label}</span>"
        if notif_count > 0 else ""
    )

    # Build notification items HTML from real data
    if notifications:
        notif_items = ""
        for n in notifications:
            type_colors = {"success": "#30d158", "warning": "#f59e0b", "error": "#ef4444", "info": "#3b82f6"}
            dot_color = type_colors.get(n.get("type", "info"), "#3b82f6")
            notif_items += f"""
            <div class='notif-item'>
                <div class='notif-title'><span style='color:{dot_color};'>●</span> {n.get('title', '')}</div>
                <div>{n.get('message', '')}</div>
            </div>"""
    else:
        notif_items = "<div class='notif-empty'>No new notifications</div>"

    return f"""
    <style>
    #{uid}-panel {{
        display: none;
        position: absolute;
        top: 52px; right: 12px;
        width: 320px;
        background: #1a1a1a;
        border: 1px solid rgba(212,175,55,0.2);
        border-radius: 12px;
        padding: 16px;
        z-index: 9999;
        box-shadow: 0 8px 40px rgba(0,0,0,0.5);
        font-family: 'Inter', sans-serif;
    }}
    #{uid}-panel .notif-item {{
        padding: 10px 0;
        border-bottom: 1px solid rgba(212,175,55,0.06);
        font-size: 0.8rem;
        color: #e2e8f0;
    }}
    #{uid}-panel .notif-title {{ font-weight:600; color:#d4af37; margin-bottom:2px; }}
    #{uid}-panel .notif-empty {{ text-align:center; color:#94a3b8; padding:12px 0; }}
    </style>

    <div style='display:flex;align-items:center;gap:12px;padding:12px 0;position:relative;flex-wrap:wrap;'>

        <!-- Brand -->
        <div style='display:flex;align-items:center;gap:10px;flex:1;'>
            <div style='width:36px;height:36px;background:linear-gradient(135deg,#d4af37,#f59e0b);
                        border-radius:10px;display:flex;align-items:center;justify-content:center;
                        font-size:1.1rem;flex-shrink:0;'>&#x1f6e1;</div>
            <div>
                <div class='brand-text'>FlagGuard</div>
                <div class='brand-subtitle'><span class='status-dot'></span>Operational</div>
            </div>
        </div>

        <!-- Notification Bell (Feature A) -->
        <div style='position:relative;cursor:pointer;' onclick='(function(){{ var p=document.getElementById("{uid}-panel"); if(p) p.style.display=p.style.display==="none"?"block":"none"; }})()' title='Notifications'>
            <span style='font-size:1.3rem;'>&#x1f514;</span>
            {notif_count_html}
        </div>

        <!-- Notification dropdown panel -->
        <div id='{uid}-panel'>
            <div style='font-family:Outfit,sans-serif;font-weight:700;color:#d4af37;margin-bottom:12px;font-size:0.9rem;'>
                &#x1f514; Notifications ({notif_count})
            </div>
            {notif_items}
        </div>

        <!-- Role Badge -->
        <span class='{badge_class}'>{role_label}</span>

        <!-- How To Use Button -->
        <a href='#' data-help='{role}' style='display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;border:1px solid rgba(99,102,241,0.4);background:rgba(99,102,241,0.1);color:#818cf8;font-family:Outfit,sans-serif;font-weight:600;font-size:0.78rem;text-decoration:none;cursor:pointer;' title='How to use this dashboard'>&#10067; How To Use</a>

    </div>

    <!-- Inject JS once -->
    {DARK_LIGHT_JS}
    """

def create_shared_header(role: str, user_state: gr.State) -> tuple:
    """Create shared header row with brand, notifications, theme toggle, role badge, sign-out.
    
    Returns: (header_html component, logout_btn, theme_btn)
    """
    header_html = gr.HTML(build_header_html(role, 0))

    # Real Gradio button for theme toggle — uses js= for reliable execution
    theme_btn = gr.Button(
        "\U0001f319 Dark", elem_classes=["theme-toggle-btn", "glass-btn"],
        size="sm", min_width=80,
    )
    theme_btn.click(
        fn=None, inputs=None, outputs=None,
        js="() => { if(window.fgToggleTheme) window.fgToggleTheme(); }"
    )

    logout_btn  = gr.Button("Sign Out", elem_classes=["glass-btn"], size="sm", min_width=90)

    def refresh_notif_header(uid):
        """Reload notification count and data when user logs in."""
        if not uid:
            return build_header_html(role, 0)
        try:
            from flagguard.core.db import SessionLocal
            from flagguard.core.models.tables import Notification
            db = SessionLocal()
            notifs = db.query(Notification).filter(
                Notification.user_id == uid,
                Notification.is_read == False
            ).order_by(Notification.created_at.desc()).limit(10).all()
            count = len(notifs)
            notif_list = [{"title": n.title, "message": n.message, "type": n.type} for n in notifs]

            return build_header_html(role, count, notif_list)
        except Exception:
            return build_header_html(role, 0)

    user_state.change(refresh_notif_header, inputs=[user_state], outputs=[header_html])

    return header_html, logout_btn, theme_btn
