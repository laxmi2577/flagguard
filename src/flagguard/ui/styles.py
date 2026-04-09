"""Shared CSS styles and Gradio theme for FlagGuard UI."""

import gradio as gr

LIQUID_GLASS_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-deep: #0f0f0f;
    --bg-surface: #1a1a1a;
    --bg-elevated: #222222;
    --gold-primary: #d4af37;
    --gold-light: #f59e0b;
    --gold-dim: #92702a;
    --platinum: #e2e8f0;
    --platinum-dim: #94a3b8;
    --emerald: #30d158;
    --ruby: #ef4444;
    --sapphire: #3b82f6;
    --font-heading: 'Outfit', sans-serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --glass-bg: rgba(255,255,255,0.03);
    --glass-border: rgba(212,175,55,0.08);
    --glass-hover: rgba(255,255,255,0.05);
    --glass-blur: 20px;
    --role-admin: #ef4444;
    --role-analyst: #f59e0b;
    --role-viewer: #94a3b8;
}

* { box-sizing: border-box; }

body, .gradio-container {
    background: var(--bg-deep) !important;
    font-family: var(--font-body) !important;
    color: var(--platinum) !important;
}

/* === GLASS CARD === */
.glass-card {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(var(--glass-blur)) !important;
    -webkit-backdrop-filter: blur(var(--glass-blur)) !important;
    padding: 24px !important;
    position: relative;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.glass-card:hover {
    background: var(--glass-hover) !important;
    border-color: rgba(212, 175, 55, 0.15) !important;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4), 0 0 60px rgba(212, 175, 55, 0.05);
    transform: translateY(-2px);
}

/* === METRIC CARDS === */
.metric-card {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    padding: 20px !important;
    text-align: center;
    backdrop-filter: blur(16px) !important;
    transition: all 0.3s ease;
}

.metric-card:hover { border-color: rgba(212,175,55,0.2) !important; }

.metric-value {
    font-family: var(--font-heading);
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--gold-primary);
    line-height: 1;
    letter-spacing: -0.02em;
}

.metric-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--platinum-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 8px;
}

/* === BUTTONS === */
.glass-btn {
    background: linear-gradient(135deg, rgba(212,175,55,0.12), rgba(212,175,55,0.04)) !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
    border-radius: 10px !important;
    color: var(--gold-primary) !important;
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    transition: all 0.2s ease !important;
}

.glass-btn:hover {
    background: linear-gradient(135deg, rgba(212,175,55,0.2), rgba(212,175,55,0.08)) !important;
    border-color: rgba(212,175,55,0.5) !important;
    box-shadow: 0 4px 20px rgba(212,175,55,0.15) !important;
    transform: translateY(-1px) !important;
}

.danger-btn {
    background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04)) !important;
    border: 1px solid rgba(239,68,68,0.3) !important;
    color: #ef4444 !important;
}

.success-btn {
    background: linear-gradient(135deg, rgba(48,209,88,0.12), rgba(48,209,88,0.04)) !important;
    border: 1px solid rgba(48,209,88,0.3) !important;
    color: var(--emerald) !important;
}

/* === SIDEBAR === */
.frosted-sidebar {
    background: rgba(255,255,255,0.02) !important;
    border-right: 1px solid var(--glass-border) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    padding: 24px !important;
    min-height: calc(100vh - 80px);
}

.sidebar-section { margin-bottom: 8px; }

.sidebar-title {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--platinum-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 12px;
}

/* === HEADER === */
.app-header {
    background: rgba(255,255,255,0.02) !important;
    border-bottom: 1px solid var(--glass-border) !important;
    padding: 16px 24px !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    position: sticky;
    top: 0;
    z-index: 100;
}

/* === ROLE BADGES === */
.badge-admin {
    background: rgba(239,68,68,0.15);
    color: #ef4444;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 1px solid rgba(239,68,68,0.3);
}
.badge-analyst {
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 1px solid rgba(245,158,11,0.3);
}
.badge-viewer {
    background: rgba(148,163,184,0.15);
    color: #94a3b8;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 1px solid rgba(148,163,184,0.3);
}

/* === ROLE INFO BANNER === */
.role-banner-viewer {
    background: linear-gradient(135deg, rgba(148,163,184,0.08), rgba(148,163,184,0.03));
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.role-banner-analyst {
    background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.03));
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.role-banner-admin {
    background: linear-gradient(135deg, rgba(239,68,68,0.08), rgba(239,68,68,0.03));
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* === STATUS DOTS === */
.status-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--emerald);
    box-shadow: 0 0 8px rgba(48,209,88,0.4);
    margin-right: 6px;
}

/* === BRAND === */
.brand-text {
    font-family: var(--font-heading);
    font-size: 1.3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #d4af37, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 0.05em;
}
.brand-subtitle {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--platinum-dim);
    letter-spacing: 0.1em;
}

/* === LOGIN === */
.login-bg { min-height: 100vh; }

.login-logo {
    width: 56px; height: 56px;
    margin: 0 auto 24px;
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-light));
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    box-shadow: 0 4px 20px rgba(212,175,55,0.3);
}
.login-title {
    font-family: var(--font-heading);
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #d4af37, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
}
.login-subtitle {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--platinum-dim);
    letter-spacing: 0.08em;
    margin-bottom: 24px;
}
.shimmer-border {
    border: 1px solid rgba(212,175,55,0.2) !important;
    box-shadow: 0 0 40px rgba(212,175,55,0.05), 0 20px 60px rgba(0,0,0,0.4) !important;
}

/* === TABS === */
.tabs > .tab-nav > button {
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
}

/* === NOTIFICATION BADGE === */
.notif-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px; height: 18px;
    background: #ef4444;
    border-radius: 50%;
    font-size: 0.65rem;
    font-weight: 700;
    color: white;
    margin-left: 4px;
    vertical-align: middle;
}

/* === GRADIO OVERRIDES === */
button {
    font-family: var(--font-heading) !important;
    transition: all 0.2s ease !important;
}
label, .label-wrap {
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--platinum-dim) !important;
}
input, textarea, select {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(212,175,55,0.15) !important;
    border-radius: 8px !important;
    color: var(--platinum) !important;
    font-family: var(--font-body) !important;
}
input:focus, textarea:focus {
    border-color: rgba(212,175,55,0.4) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(212,175,55,0.05) !important;
}

/* === DARK/LIGHT TOGGLE === */
body.light-mode {
    --bg-deep: #f8f9fa;
    --bg-surface: #ffffff;
    --bg-elevated: #f1f5f9;
    --glass-bg: rgba(0,0,0,0.02);
    --glass-border: rgba(212,175,55,0.2);
    --glass-hover: rgba(0,0,0,0.04);
    --platinum: #1e293b;
    --platinum-dim: #475569;
}
body.light-mode .gradio-container { background: #f8f9fa !important; }
body.light-mode input,
body.light-mode textarea,
body.light-mode select {
    background: #ffffff !important;
    border-color: rgba(212,175,55,0.25) !important;
    color: #1e293b !important;
}
body.light-mode .glass-card {
    background: rgba(255,255,255,0.8) !important;
    border-color: rgba(212,175,55,0.2) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
}
body.light-mode .metric-card {
    background: rgba(255,255,255,0.6) !important;
    border-color: rgba(212,175,55,0.15) !important;
}
body.light-mode .glass-btn {
    background: linear-gradient(135deg, rgba(212,175,55,0.1), rgba(212,175,55,0.04)) !important;
    color: #92702a !important;
}
body.light-mode label, body.light-mode .label-wrap {
    color: #475569 !important;
}
body.light-mode .app-header {
    background: rgba(255,255,255,0.9) !important;
    border-color: rgba(212,175,55,0.15) !important;
}
body.light-mode .frosted-sidebar {
    background: rgba(255,255,255,0.5) !important;
}
body.light-mode .sidebar-title { color: #475569; }
body.light-mode .brand-subtitle { color: #64748b; }
body.light-mode [id$="-panel"] {
    background: #ffffff !important;
    border-color: rgba(212,175,55,0.2) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.1) !important;
}
body.light-mode [id$="-panel"] .notif-item { color: #334155 !important; }
body.light-mode .role-banner-admin,
body.light-mode .role-banner-analyst,
body.light-mode .role-banner-viewer {
    background: rgba(255,255,255,0.5) !important;
}

/* === WCAG 2.2 AA: Reduced Motion Support === */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}

/* === WCAG 2.2 AA: Keyboard Focus Visibility === */
*:focus-visible {
    outline: 2px solid var(--gold-primary) !important;
    outline-offset: 2px !important;
    border-radius: 4px;
}

/* Remove focus outline for mouse users */
*:focus:not(:focus-visible) {
    outline: none !important;
}

/* === Skip to Main Content (Accessibility) === */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--gold-primary);
    color: #000;
    padding: 8px;
    z-index: 100;
    transition: top 0.2s;
}
.skip-link:focus {
    top: 0;
}

"""


def get_theme():
    return gr.themes.Soft(
        primary_hue=gr.themes.Color(
            c50="#fefce8", c100="#fef9c3", c200="#fef08a",
            c300="#fde047", c400="#f59e0b", c500="#d4af37",
            c600="#b8962f", c700="#92702a", c800="#6b5220",
            c900="#4a3a16", c950="#2a2008",
        ),
        neutral_hue="stone",
    )
