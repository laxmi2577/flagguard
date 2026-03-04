"""Shared header component for all role dashboards.

Provides:
- Brand logo + status dot
- Dark / Light mode toggle (Feature D)
- Notification bell with unread count dropdown (Feature A)
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

    // Global toggle function called by Gradio button
    window.fgToggleTheme = function() {
        var isLight = document.body.classList.toggle('light-mode');
        localStorage.setItem('fg_theme', isLight ? 'light' : 'dark');
        var btn = document.getElementById('theme-toggle-btn');
        if (btn) btn.innerHTML = isLight ? '☀️ Light' : '🌙 Dark';
    };
})();
</script>
"""

NOTIF_PANEL_JS = """
<script>
window.fgToggleNotif = function() {
    var panel = document.getElementById('notif-panel');
    if (panel) panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
};
</script>
"""


def build_header_html(role: str, notif_count: int = 0) -> str:
    """Build the full header HTML with brand, notifications, theme toggle and role badge."""
    badge_class = f"badge-{role}"
    role_label  = role.upper()

    notif_color  = "#ef4444" if notif_count > 0 else "#555"
    notif_count_label = str(notif_count) if notif_count <= 9 else "9+"
    notif_count_html  = (
        f"<span style='position:absolute;top:-4px;right:-4px;background:#ef4444;color:#fff;"
        f"border-radius:50%;width:16px;height:16px;font-size:0.6rem;font-weight:700;"
        f"display:flex;align-items:center;justify-content:center;'>{notif_count_label}</span>"
        if notif_count > 0 else ""
    )

    return f"""
    <style>
    #notif-panel {{
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
    #notif-panel .notif-item {{
        padding: 10px 0;
        border-bottom: 1px solid rgba(212,175,55,0.06);
        font-size: 0.8rem;
        color: #e2e8f0;
    }}
    #notif-panel .notif-title {{ font-weight:600; color:#d4af37; margin-bottom:2px; }}
    #notif-panel .notif-empty {{ text-align:center; color:#94a3b8; padding:12px 0; }}
    </style>

    <div style='display:flex;align-items:center;gap:12px;padding:12px 0;position:relative;flex-wrap:wrap;'>

        <!-- Brand -->
        <div style='display:flex;align-items:center;gap:10px;flex:1;'>
            <div style='width:36px;height:36px;background:linear-gradient(135deg,#d4af37,#f59e0b);
                        border-radius:10px;display:flex;align-items:center;justify-content:center;
                        font-size:1.1rem;flex-shrink:0;'>🛡</div>
            <div>
                <div class='brand-text'>FlagGuard</div>
                <div class='brand-subtitle'><span class='status-dot'></span>Operational</div>
            </div>
        </div>

        <!-- Notification Bell (Feature A) -->
        <div style='position:relative;cursor:pointer;' onclick='fgToggleNotif()' title='Notifications'>
            <span style='font-size:1.3rem;'>🔔</span>
            {notif_count_html}
        </div>

        <!-- Notification dropdown panel -->
        <div id='notif-panel'>
            <div style='font-family:Outfit,sans-serif;font-weight:700;color:#d4af37;margin-bottom:12px;font-size:0.9rem;'>
                🔔 Notifications
            </div>
            <div id='notif-list' class='notif-empty'>Loading...</div>
        </div>

        <!-- Dark/Light Toggle (Feature D) -->
        <button id='theme-toggle-btn'
            onclick='fgToggleTheme()'
            style='background:rgba(255,255,255,0.05);border:1px solid rgba(212,175,55,0.2);
                   border-radius:8px;color:#94a3b8;font-size:0.75rem;cursor:pointer;
                   padding:5px 12px;transition:all 0.2s;'
            title='Toggle dark/light mode'>
            🌙 Dark
        </button>

        <!-- Role Badge -->
        <span class='{badge_class}'>{role_label}</span>

    </div>

    <!-- Inject JS once -->
    {DARK_LIGHT_JS}
    {NOTIF_PANEL_JS}
    """


def create_shared_header(role: str, user_state: gr.State) -> tuple:
    """Create shared header row with brand, notifications, theme toggle, role badge, sign-out.
    
    Returns: (header_html component, logout_btn)
    """
    header_html = gr.HTML(build_header_html(role, 0))
    logout_btn  = gr.Button("Sign Out", elem_classes=["glass-btn"], size="sm", min_width=90)

    def refresh_notif_header(uid):
        """Reload notification count when user logs in."""
        if not uid:
            return build_header_html(role, 0)
        try:
            from flagguard.core.db import SessionLocal
            from flagguard.core.models.tables import Notification
            db = SessionLocal()
            count = db.query(Notification).filter(
                Notification.user_id == uid,
                Notification.is_read == False
            ).count()
            db.close()
            return build_header_html(role, count)
        except Exception:
            return build_header_html(role, 0)

    user_state.change(refresh_notif_header, inputs=[user_state], outputs=[header_html])

    return header_html, logout_btn
