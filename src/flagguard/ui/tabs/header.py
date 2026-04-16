"""Shared header component for all role dashboards.

Provides:
- Brand logo + status dot
- Dark / Light mode toggle
- Notification bell with unread count — loads real data from DB
- Role badge
- How To Use button
- Sign Out button
All rendered in a single clean header row.
"""

import gradio as gr


def build_header_html(role: str, notif_count: int = 0, notifications: list = None) -> str:
    """Build the full header HTML with brand, notifications, theme toggle, role badge, help, and sign-out."""
    badge_class = f"badge-{role}"
    role_label  = role.upper()
    uid = f"notif-{role}"

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

    /* Hide the Gradio logout/theme buttons — they exist in DOM for JS click only */
    .fg-hidden-logout {{ position:absolute !important; width:1px !important; height:1px !important; overflow:hidden !important; clip:rect(0,0,0,0) !important; opacity:0 !important; pointer-events:none !important; }}

    /* ── Header action buttons ─────────────────────────────── */
    .fg-header-actions {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }}
    .fg-hdr-btn {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 12px;
        border-radius: 8px;
        border: 1px solid rgba(212,175,55,0.25);
        background: rgba(212,175,55,0.08);
        color: #d4af37;
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        white-space: nowrap;
        line-height: 1.4;
    }}
    .fg-hdr-btn:hover {{
        background: rgba(212,175,55,0.18);
        border-color: rgba(212,175,55,0.5);
        transform: translateY(-1px);
    }}
    .fg-hdr-btn.fg-signout {{
        border-color: rgba(239,68,68,0.3);
        background: rgba(239,68,68,0.08);
        color: #f87171;
    }}
    .fg-hdr-btn.fg-signout:hover {{
        background: rgba(239,68,68,0.2);
        border-color: rgba(239,68,68,0.5);
    }}
    .fg-hdr-btn.fg-help {{
        border-color: rgba(99,102,241,0.4);
        background: rgba(99,102,241,0.1);
        color: #818cf8;
    }}
    .fg-hdr-btn.fg-help:hover {{
        background: rgba(99,102,241,0.2);
        border-color: rgba(99,102,241,0.6);
    }}
    /* Light mode overrides */
    body.light-mode .fg-hdr-btn {{
        background: rgba(212,175,55,0.12);
    }}
    body.light-mode .fg-hdr-btn.fg-signout {{
        background: rgba(239,68,68,0.1);
    }}
    body.light-mode .fg-hdr-btn.fg-help {{
        background: rgba(99,102,241,0.12);
    }}
    </style>

    <div style='display:flex;align-items:center;gap:12px;padding:10px 0;position:relative;'>

        <!-- Brand -->
        <div style='display:flex;align-items:center;gap:10px;flex:1;'>
            <div style='width:40px;height:40px;flex-shrink:0;'>
                <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:40px;height:40px;">
                  <defs>
                    <linearGradient id="hdr-bg" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stop-color="#0f0f1a"/>
                      <stop offset="100%" stop-color="#1a1a2e"/>
                    </linearGradient>
                    <linearGradient id="hdr-gold" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stop-color="#f59e0b"/>
                      <stop offset="100%" stop-color="#d4af37"/>
                    </linearGradient>
                  </defs>
                  <rect width="40" height="40" rx="10" fill="url(#hdr-bg)"/>
                  <!-- Shield body -->
                  <path d="M20 5 L32 10 L32 22 C32 28.5 26.5 33.5 20 35 C13.5 33.5 8 28.5 8 22 L8 10 Z" fill="none" stroke="url(#hdr-gold)" stroke-width="1.5" stroke-linejoin="round"/>
                  <!-- Flag pennant inside shield -->
                  <line x1="16" y1="13" x2="16" y2="27" stroke="#d4af37" stroke-width="1.5" stroke-linecap="round"/>
                  <path d="M16 13 L24 16 L16 19 Z" fill="#d4af37"/>
                  <!-- AI circuit dots -->
                  <circle cx="20" cy="5" r="1" fill="#3b82f6" opacity="0.8"/>
                  <circle cx="32" cy="10" r="1" fill="#3b82f6" opacity="0.8"/>
                  <circle cx="32" cy="22" r="1" fill="#3b82f6" opacity="0.6"/>
                  <circle cx="8" cy="10" r="1" fill="#3b82f6" opacity="0.8"/>
                  <circle cx="8" cy="22" r="1" fill="#3b82f6" opacity="0.6"/>
                  <!-- Glow pulse ring -->
                  <circle cx="20" cy="20" r="18" stroke="#d4af37" stroke-width="0.3" opacity="0.2"/>
                </svg>
              </div>
            <div>
                <div class='brand-text'>FlagGuard</div>
                <div class='brand-subtitle'><span class='status-dot'></span>Operational</div>
            </div>
        </div>

        <!-- Right side: all action buttons in one row -->
        <div class='fg-header-actions'>

            <!-- Notification Bell -->
            <div style='position:relative;cursor:pointer;padding:4px;' data-action='toggle-notif' data-notif-panel='{uid}-panel' title='Notifications'>
                <span style='font-size:1.2rem;'>&#x1f514;</span>
                {notif_count_html}
            </div>

            <!-- Role Badge -->
            <span class='{badge_class}' style='margin:0 2px;'>{role_label}</span>

            <!-- How To Use -->
            <a href='#' data-help='{role}' class='fg-hdr-btn fg-help' title='How to use this dashboard'>&#10067; How To Use</a>

            <!-- Dark/Light Toggle -->
            <button class='fg-hdr-btn' id='fg-theme-toggle' data-action='toggle-theme' title='Toggle dark/light mode'>
                🌙 Dark
            </button>

            <!-- Sign Out -->
            <button class='fg-hdr-btn fg-signout' id='fg-signout-btn' data-action='sign-out' title='Sign out'>
                🚪 Sign Out
            </button>

        </div>

        <!-- Notification dropdown panel -->
        <div id='{uid}-panel'>
            <div style='font-family:Outfit,sans-serif;font-weight:700;color:#d4af37;margin-bottom:12px;font-size:0.9rem;'>
                &#x1f514; Notifications ({notif_count})
            </div>
            {notif_items}
        </div>

    </div>
    """

def create_shared_header(role: str, user_state: gr.State) -> tuple:
    """Create shared header row with brand, notifications, theme toggle, role badge, sign-out.

    Returns: (header_html component, logout_btn, theme_btn)
    The logout_btn is hidden — triggered by the HTML sign-out button via JS.
    theme_btn is a dummy for backward compatibility.
    """
    header_html = gr.HTML(build_header_html(role, 0))

    # Hidden Gradio logout button — the HTML "Sign Out" button clicks this via JS
    # NOTE: We use visible=True + CSS hiding (not visible=False) because
    # Gradio's visible=False may not render the element in the DOM at all,
    # which would break the JS querySelector click trigger.
    logout_btn = gr.Button(
        "Sign Out", elem_classes=["fg-hidden-logout"],
        size="sm", min_width=1,
    )

    # Dummy theme button (no longer rendered, kept for API compatibility)
    theme_btn = gr.Button(
        "Theme", elem_classes=["fg-hidden-logout"], size="sm", min_width=1,
    )

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
