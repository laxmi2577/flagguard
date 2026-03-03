"""FlagGuard Enterprise — Liquid Glass Edition.

Features:
- Royal Obsidian Theme (Black/Gold/Silver)
- Liquid Glass Effects (Frosted panels, Refraction, Shimmer)
- Premium Typography (Outfit + Inter)
- Gold/Emerald Chart Palette
- Floating Orb Login Concept
- Enterprise-Grade Professional Interface
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
import base64
import tempfile
import io
import uuid

import gradio as gr
try:
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: Plotly not found. Charts will be disabled.")

from flagguard import __version__
from flagguard.core.models import ConflictType
from flagguard.ui.tabs.chat import create_chat_tab


# History storage path
HISTORY_FILE = Path.home() / ".flagguard" / "analysis_history.json"

# --- LIQUID GLASS THEME (Royal Obsidian) ---

LIQUID_GLASS_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    /* Royal Obsidian Palette */
    --bg-deep: #0f0f0f;
    --bg-surface: #1a1a1a;
    --bg-elevated: #222222;
    --gold-primary: #d4af37;
    --gold-light: #f59e0b;
    --gold-dim: #92702a;
    --platinum: #e2e8f0;
    --platinum-dim: #94a3b8;
    --emerald: #30d158;
    --emerald-dim: #22a847;
    --crimson: #dc2626;
    --crimson-dim: #991b1b;

    /* Glass Materials */
    --glass-bg: rgba(255, 255, 255, 0.03);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-hover: rgba(255, 255, 255, 0.06);
    --glass-blur: 20px;

    /* Typography */
    --font-heading: 'Outfit', sans-serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}

/* === BASE === */
body, .gradio-container {
    background: linear-gradient(160deg, var(--bg-deep) 0%, #111111 40%, var(--bg-surface) 100%) !important;
    color: var(--platinum) !important;
    font-family: var(--font-body) !important;
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

/* === SHIMMER BORDER (ANIMATED) === */
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.shimmer-border {
    position: relative;
    border: none !important;
    overflow: hidden;
}

.shimmer-border::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 16px;
    padding: 1px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(212,175,55,0.0) 25%,
        rgba(212,175,55,0.3) 50%,
        rgba(212,175,55,0.0) 75%,
        transparent 100%
    );
    background-size: 200% 100%;
    animation: shimmer 4s linear infinite;
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
}

/* === METRIC DISPLAY === */
.metric-card {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    padding: 20px !important;
    text-align: center;
    backdrop-filter: blur(16px) !important;
    transition: all 0.3s ease;
}

.metric-card:hover {
    border-color: rgba(212,175,55,0.2) !important;
}

.metric-value {
    font-family: var(--font-heading);
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--gold-primary);
    line-height: 1;
    letter-spacing: -0.02em;
}

.metric-label {
    font-family: var(--font-heading);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--platinum-dim);
    margin-top: 8px;
}

/* === GLASS BUTTON === */
.glass-btn {
    background: linear-gradient(135deg, rgba(212,175,55,0.15) 0%, rgba(212,175,55,0.05) 100%) !important;
    border: 1px solid rgba(212,175,55,0.3) !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    color: var(--gold-primary) !important;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
    position: relative;
    overflow: hidden;
}

.glass-btn:hover {
    background: linear-gradient(135deg, rgba(212,175,55,0.25) 0%, rgba(212,175,55,0.1) 100%) !important;
    border-color: rgba(212,175,55,0.5) !important;
    box-shadow: 0 4px 20px rgba(212,175,55,0.15) !important;
    transform: translateY(-1px) !important;
}

.glass-btn:active {
    transform: translateY(0) !important;
}

/* === FROSTED SIDEBAR === */
.frosted-sidebar {
    background: rgba(255,255,255,0.02) !important;
    border-right: 1px solid var(--glass-border) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    padding: 24px 16px !important;
    min-height: 100vh;
}

.sidebar-section {
    margin-bottom: 24px;
}

.sidebar-title {
    font-family: var(--font-heading);
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--gold-dim);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(212,175,55,0.1);
}

/* === HEADER === */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid var(--glass-border);
    background: rgba(255,255,255,0.01);
    backdrop-filter: blur(16px);
}

.brand-text {
    font-family: var(--font-heading);
    font-size: 1.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-light));
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

.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--emerald);
    box-shadow: 0 0 8px rgba(48,209,88,0.4);
    margin-right: 6px;
}

/* === FLOATING ORB (LOGIN BG) === */
@keyframes orbFloat {
    0%, 100% { transform: translate(-50%, -50%) scale(1); }
    33%      { transform: translate(-48%, -52%) scale(1.05); }
    66%      { transform: translate(-52%, -48%) scale(0.95); }
}

@keyframes orbGlow {
    0%, 100% { opacity: 0.4; }
    50%      { opacity: 0.6; }
}

.login-bg {
    position: relative;
    min-height: 100vh;
    overflow: hidden;
}

.login-bg::before {
    content: '';
    position: absolute;
    top: 40%;
    left: 50%;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle,
        rgba(212,175,55,0.15) 0%,
        rgba(212,175,55,0.05) 40%,
        transparent 70%
    );
    filter: blur(60px);
    animation: orbFloat 8s ease-in-out infinite, orbGlow 4s ease-in-out infinite;
    pointer-events: none;
}

.login-card {
    background: var(--glass-bg) !important;
    border: 1px solid rgba(212,175,55,0.15) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(30px) !important;
    -webkit-backdrop-filter: blur(30px) !important;
    padding: 40px !important;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
    max-width: 420px;
    margin: 0 auto;
}

.login-logo {
    width: 56px;
    height: 56px;
    margin: 0 auto 24px;
    background: linear-gradient(135deg, var(--gold-primary), var(--gold-light));
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    box-shadow: 0 4px 20px rgba(212,175,55,0.2);
}

.login-title {
    font-family: var(--font-heading);
    font-size: 1.8rem;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(135deg, var(--platinum), #ffffff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
}

.login-subtitle {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--platinum-dim);
    text-align: center;
    margin-bottom: 32px;
}

/* === AI TOGGLE === */
.ai-toggle-container {
    padding: 10px 14px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: all 0.3s ease;
    font-family: var(--font-body);
    font-size: 0.85rem;
}

.ai-toggle-on {
    background: rgba(48,209,88,0.08) !important;
    border: 1px solid rgba(48,209,88,0.2) !important;
    color: var(--emerald) !important;
}

.ai-toggle-off {
    background: rgba(148,163,184,0.05) !important;
    border: 1px solid rgba(148,163,184,0.1) !important;
    color: var(--platinum-dim) !important;
}

/* === GRADIO OVERRIDES === */
button {
    background: linear-gradient(135deg, rgba(212,175,55,0.12), rgba(212,175,55,0.04)) !important;
    border: 1px solid rgba(212,175,55,0.2) !important;
    border-radius: 10px !important;
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    color: var(--gold-primary) !important;
    transition: all 0.3s ease !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-size: 0.8rem !important;
}

button:hover {
    background: linear-gradient(135deg, rgba(212,175,55,0.2), rgba(212,175,55,0.08)) !important;
    border-color: rgba(212,175,55,0.4) !important;
    box-shadow: 0 4px 16px rgba(212,175,55,0.1) !important;
}

input, textarea, select, .gr-input {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    color: var(--platinum) !important;
    font-family: var(--font-body) !important;
}

input:focus, textarea:focus {
    border-color: rgba(212,175,55,0.3) !important;
    box-shadow: 0 0 0 3px rgba(212,175,55,0.08) !important;
}

label, .gr-form label {
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--platinum-dim) !important;
}

.tabs > .tab-nav > button {
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    border-radius: 8px 8px 0 0 !important;
}

.tabs > .tab-nav > button.selected {
    border-bottom: 2px solid var(--gold-primary) !important;
    color: var(--gold-primary) !important;
}

/* === FOOTER === */
footer {
    background: rgba(15,15,15,0.8) !important;
    border-top: 1px solid var(--glass-border) !important;
    backdrop-filter: blur(16px) !important;
    padding: 12px 24px !important;
}

footer a, footer span {
    color: var(--platinum-dim) !important;
    font-family: var(--font-body) !important;
    font-size: 0.75rem !important;
}

/* === MERMAID CODE PANEL === */
.mermaid-code-section textarea {
    font-size: 0.8rem !important;
    line-height: 1.6 !important;
    background: rgba(0,0,0,0.3) !important;
    color: var(--emerald) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    font-family: var(--font-mono) !important;
    padding: 16px !important;
}

.mermaid-code-section .label-wrap {
    color: var(--gold-dim) !important;
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
}

/* === RIPPLE LOADING === */
@keyframes ripple {
    0%   { transform: scale(0.8); opacity: 1; }
    100% { transform: scale(2.5); opacity: 0; }
}

.loading-ripple {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--gold-primary);
    animation: ripple 1.5s ease-out infinite;
}
"""

def create_charts(flags: list, conflicts: list):
    """Generate charts with Gold/Emerald/Silver palette."""
    if not PLOTLY_AVAILABLE:
        return None, None
    
    # 1. Radial Gauge for Flags Status
    enabled_count = sum(1 for f in flags if f.enabled)
    disabled_count = len(flags) - enabled_count
    total = len(flags)
    
    # Create a donut gauge
    fig1 = go.Figure(data=[go.Pie(
        labels=['Active', 'Inactive'],
        values=[enabled_count, disabled_count],
        hole=.75,
        marker_colors=['#d4af37', '#333333'],
        textinfo='none',
        hoverinfo='label+value',
        showlegend=False
    )])
    
    # Add center annotation
    fig1.add_annotation(
        text=f"<b>{total}</b>",
        x=0.5, y=0.55,
        font_size=48,
        font_color="#d4af37",
        showarrow=False
    )
    fig1.add_annotation(
        text="TOTAL FLAGS",
        x=0.5, y=0.4,
        font_size=12,
        font_color="#94a3b8",
        showarrow=False
    )
    
    fig1.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20),
        height=280,
        font=dict(family="Outfit")
    )

    # 2. Bar Chart - Severity (Industrial Style)
    severities = {}
    for c in conflicts:
        s = str(c.severity.value).upper() if hasattr(c, 'severity') else 'MEDIUM'
        severities[s] = severities.get(s, 0) + 1
    
    if not severities:
        severities = {'NONE': 0}
    
    order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    counts = [severities.get(s, 0) for s in order]
    colors = ['#dc2626', '#d4af37', '#f59e0b', '#30d158']
    
    filtered_data = [(l, c, col) for l, c, col in zip(order, counts, colors) if c > 0]
    if not filtered_data:
        filtered_data = [('OPERATIONAL', 0, '#30d158')]
    
    f_labels, f_counts, f_colors = zip(*filtered_data) if filtered_data else ([], [], [])
    
    fig2 = go.Figure(data=[go.Bar(
        x=f_labels,
        y=f_counts,
        marker=dict(
            color=f_colors,
            line=dict(color='#1a1a1a', width=2)
        ),
        text=f_counts,
        textposition='outside',
        textfont=dict(color='#d4af37', size=14, family='JetBrains Mono')
    )])
    
    fig2.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,26,26,0.3)',
        font=dict(family="Outfit", color="#94a3b8"),
        margin=dict(t=40, b=40, l=40, r=40),
        height=280,
        xaxis=dict(
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(212,175,55,0.1)',
            zeroline=False
        ),
        title=dict(
            text="Conflict Severity",
            font=dict(size=14, color='#d4af37'),
            x=0.5,
            xanchor='center'
        )
    )
    
    return fig1, fig2


def load_history() -> list[dict]:
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return []

def save_history_entry(entry: dict):
    try:
        history = load_history()
        history.insert(0, entry)
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[:50], f)
    except:
        pass


# --- ANALYSIS LOGIC ---

def analyze_and_update_ui(
    config_file, source_file, use_llm,
    progress=gr.Progress()
):
    if not config_file:
        return [0, 0, 0, 0, "0%", None, None, "", "", ""] 
        
    try:
        progress(0.1, desc="INITIALIZING SYSTEM...")
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector
        from flagguard.reporters import MarkdownReporter
        
        flags = parse_config(Path(config_file.name))
        
        progress(0.4, desc="SCANNING DEPENDENCIES...")
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        mutual_exclusions = [c for c in conflicts if c.conflict_type == ConflictType.MUTUAL_EXCLUSION]
        dependency_violations = [c for c in conflicts if c.conflict_type == ConflictType.DEPENDENCY_VIOLATION]
        
        summary = ""
        if use_llm and conflicts:
            progress(0.6, desc="AI ANALYSIS IN PROGRESS...")
            try:
                from flagguard.llm import OllamaClient, ExplanationEngine
                client = OllamaClient()
                if client.is_available:
                    engine = ExplanationEngine(client)
                    for c in conflicts[:5]:
                        c.llm_explanation = engine.explain_conflict(c)
                    summary = engine.generate_executive_summary(len(flags), conflicts, [])
            except:
                pass

        progress(0.8, desc="GENERATING DIAGNOSTICS...")
        
        m_flags = len(flags)
        m_conflicts = len(mutual_exclusions)
        m_dependencies = len(dependency_violations)
        m_enabled = sum(1 for f in flags if f.enabled)
        
        total_issues = len(conflicts)
        health_ratio = 1 - (total_issues / len(flags) if len(flags) > 0 else 0)
        m_health = f"{int(max(0, health_ratio) * 100)}%"
        
        fig1, fig2 = create_charts(flags, conflicts)
        
        reporter = MarkdownReporter()
        report_md = reporter.generate_report(flags, conflicts, [], summary)
        
        # Mermaid Graph
        graph_def = ["flowchart TD"]
        for f in flags:
            style = ":::active" if f.enabled else ":::inactive"
            name = f.name.replace("-", "_")
            graph_def.append(f'    {name}["{f.name}"]{style}')
            for dep in f.dependencies:
                dep_name = dep.replace("-", "_")
                graph_def.append(f"    {name} -->|REQUIRES| {dep_name}")
        
        for c in conflicts:
            if len(c.flags_involved) >= 2:
                f1 = c.flags_involved[0].replace("-", "_")
                f2 = c.flags_involved[1].replace("-", "_")
                if c.conflict_type == ConflictType.MUTUAL_EXCLUSION:
                    graph_def.append(f"    {f1} x--x {f2}")
                    graph_def.append(f"    {f1}:::conflict")
                    graph_def.append(f"    {f2}:::conflict")
                elif c.conflict_type == ConflictType.DEPENDENCY_VIOLATION:
                    graph_def.append(f"    {f1} ==>|MISSING| {f2}")
                    graph_def.append(f"    {f1}:::violation")
        
        # Industrial Mermaid Theme with Enhanced Styling
        graph_def.append("    classDef active fill:#d4af37,stroke:#b8962f,stroke-width:3px,color:#000,font-weight:bold")
        graph_def.append("    classDef inactive fill:#333333,stroke:#555555,stroke-width:2px,color:#94a3b8")
        graph_def.append("    classDef conflict fill:#dc2626,stroke:#991b1b,stroke-width:3px,color:#fff,font-weight:bold")
        graph_def.append("    classDef violation fill:#f59e0b,stroke:#d4af37,stroke-width:3px,color:#000,font-weight:bold")
        
        mermaid_code = "\n".join(graph_def)
        
        # Enhanced Industrial Grid Background HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700&family=JetBrains+Mono:wght@400&display=swap');
                
                body {{ 
                    margin: 0; 
                    background: 
                        linear-gradient(135deg, rgba(10,25,41,0.95) 0%, rgba(30,58,95,0.95) 100%),
                        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(212,175,55,0.05) 2px, rgba(212,175,55,0.05) 4px),
                        repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(212,175,55,0.05) 2px, rgba(212,175,55,0.05) 4px);
                    overflow: hidden;
                    font-family: 'JetBrains Mono', monospace;
                }}
                
                #container {{ 
                    width: 100%; 
                    height: 700px; 
                    display: flex; 
                    flex-direction: column;
                    padding: 20px;
                    box-sizing: border-box;
                    position: relative;
                }}
                
                /* Technical Header */
                .graph-header {{
                    background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
                    border: 1px solid rgba(212,175,55,0.2);
                    border-radius: 8px;
                    padding: 12px 20px;
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 
                        0 0 20px rgba(212,175,55,0.3),
                        inset 0 1px 0 rgba(255,255,255,0.1);
                }}
                
                .graph-title {{
                    font-family: 'Outfit', sans-serif;
                    font-size: 1.2rem;
                    font-weight: 700;
                    color: #d4af37;
                    text-shadow: 0 0 10px rgba(212,175,55,0.5);
                    letter-spacing: 0.1em;
                }}
                
                .graph-status {{
                    display: flex;
                    gap: 16px;
                    font-size: 0.75rem;
                    color: #94a3b8;
                }}
                
                .status-item {{
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}
                
                .status-led {{
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    box-shadow: 0 0 8px currentColor;
                }}
                
                .led-active {{ background: #00d4ff; color: #d4af37; }}
                .led-inactive {{ background: #2a4a6a; color: #2a4a6a; }}
                .led-conflict {{ background: #ff3b30; color: #ff3b30; }}
                .led-violation {{ background: #ff9500; color: #ff9500; }}
                
                /* Graph Container with 3D Panel Effect */
                .graph-panel {{
                    flex: 1;
                    background: 
                        linear-gradient(145deg, #1e3a5f 0%, #152940 100%);
                    border: 3px solid #0d1f35;
                    border-radius: 12px;
                    padding: 20px;
                    position: relative;
                    box-shadow: 
                        0 8px 24px rgba(0,0,0,0.5),
                        inset 0 2px 0 rgba(255,255,255,0.05),
                        inset 0 -2px 0 rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                
                /* Decorative Corner Elements */
                .graph-panel::before,
                .graph-panel::after {{
                    content: '';
                    position: absolute;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: radial-gradient(circle at 30% 30%, #a0a0a0, #505050);
                    box-shadow: inset 1px 1px 3px rgba(0,0,0,0.5);
                    z-index: 10;
                }}
                
                .graph-panel::before {{
                    top: 15px;
                    left: 15px;
                }}
                
                .graph-panel::after {{
                    top: 15px;
                    right: 15px;
                }}
                
                /* Holographic Grid Overlay */
                .holo-grid {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-image: 
                        linear-gradient(rgba(212,175,55,0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(212,175,55,0.03) 1px, transparent 1px);
                    background-size: 30px 30px;
                    pointer-events: none;
                    z-index: 1;
                }}
                
                .mermaid {{ 
                    width: 100%; 
                    height: 100%; 
                    position: relative;
                    z-index: 2;
                }}
                
                /* Mermaid SVG Enhancements */
                .mermaid svg {{
                    font-family: 'JetBrains Mono', monospace !important;
                }}
                
                /* Control Panel */
                .graph-controls {{
                    position: absolute;
                    bottom: 30px;
                    right: 30px;
                    background: rgba(15,15,15,0.9);
                    border: 1px solid rgba(212,175,55,0.2);
                    border-radius: 6px;
                    padding: 8px;
                    display: flex;
                    gap: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                    z-index: 100;
                }}
                
                .control-btn {{
                    background: linear-gradient(135deg, rgba(212,175,55,0.1), rgba(212,175,55,0.03));
                    border: 1px solid #94a3b8;
                    color: #d4af37;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.75rem;
                    font-family: 'Outfit', sans-serif;
                    transition: all 0.2s;
                }}
                
                .control-btn:hover {{
                    background: linear-gradient(to bottom, #3a5a7a, #2e4a6f);
                    box-shadow: 0 0 8px rgba(212,175,55,0.5);
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
        </head>
        <body>
            <div id="container">
                <div class="graph-header">
                    <div class="graph-title">⚡ DEPENDENCY GRAPH - SYSTEM TOPOLOGY</div>
                    <div class="graph-status">
                        <div class="status-item">
                            <span class="status-led led-active"></span>
                            <span>ACTIVE</span>
                        </div>
                        <div class="status-item">
                            <span class="status-led led-inactive"></span>
                            <span>INACTIVE</span>
                        </div>
                        <div class="status-item">
                            <span class="status-led led-conflict"></span>
                            <span>CONFLICT</span>
                        </div>
                        <div class="status-item">
                            <span class="status-led led-violation"></span>
                            <span>VIOLATION</span>
                        </div>
                    </div>
                </div>
                
                <div class="graph-panel">
                    <div class="holo-grid"></div>
                    <div class="mermaid">{mermaid_code}</div>
                    <div class="graph-controls" id="controls">
                        <button class="control-btn" onclick="zoomIn()">🔍 +</button>
                        <button class="control-btn" onclick="zoomOut()">🔍 -</button>
                        <button class="control-btn" onclick="resetZoom()">⟲ RESET</button>
                    </div>
                </div>
            </div>
            
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                
                mermaid.initialize({{ 
                    startOnLoad: false, 
                    theme: 'dark',
                    themeVariables: {{
                        darkMode: true,
                        background: '#0a1929',
                        primaryColor: '#00d4ff',
                        primaryTextColor: '#000',
                        primaryBorderColor: '#94a3b8',
                        lineColor: '#00d4ff',
                        secondaryColor: '#2a4a6a',
                        tertiaryColor: '#1e3a5f'
                    }},
                    flowchart: {{ 
                        htmlLabels: true, 
                        curve: 'basis',
                        padding: 20,
                        nodeSpacing: 80,
                        rankSpacing: 100
                    }} 
                }});
                
                const element = document.querySelector('.mermaid');
                await mermaid.run({{ nodes: [element] }});
                
                const svg = element.querySelector('svg');
                let panZoom;
                
                if (svg) {{
                    svg.style.height = '100%';
                    svg.style.width = '100%';
                    
                    // Initialize pan-zoom
                    panZoom = svgPanZoom(svg, {{ 
                        zoomEnabled: true, 
                        controlIconsEnabled: false,
                        fit: true, 
                        center: true,
                        minZoom: 0.3,
                        maxZoom: 5,
                        zoomScaleSensitivity: 0.3
                    }});
                    
                    // Make zoom functions global
                    window.zoomIn = () => panZoom.zoomIn();
                    window.zoomOut = () => panZoom.zoomOut();
                    window.resetZoom = () => {{ panZoom.reset(); panZoom.center(); }};
                }}
            </script>
        </body>
        </html>
        """
        encoded_html = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
        iframe_html = f'<iframe src="data:text/html;base64,{encoded_html}" style="width:100%; height:600px; border:none;"></iframe>'
        
        save_history_entry({
            "date": datetime.now().isoformat(),
            "config_file": Path(config_file.name).name,
            "flags_count": m_flags,
            "conflicts_count": len(conflicts)
        })
        
        return (
            m_flags, m_conflicts, m_dependencies, m_enabled, m_health,
            fig1, fig2, report_md, iframe_html, mermaid_code
        )

    except Exception as e:
        raise gr.Error(f"SYSTEM ERROR: {str(e)}")

def format_conflicts_list(conflicts):
    if not conflicts:
        return "✅ ALL SYSTEMS OPERATIONAL"
    text = ""
    for c in conflicts:
        icon = "🔴" if c.conflict_type == ConflictType.MUTUAL_EXCLUSION else "🟠"
        text += f"{icon} {c.conflict_id}\n"
    return text


# --- APP LAYOUT ---

def create_app():
    theme = gr.themes.Soft(
        primary_hue=gr.themes.Color(
            c50="#fefce8", c100="#fef9c3", c200="#fef08a",
            c300="#fde047", c400="#f59e0b", c500="#d4af37",
            c600="#b8962f", c700="#92702a", c800="#6b5220",
            c900="#4a3a16", c950="#2a2008",
        ),
        neutral_hue="stone",
    )
    
    with gr.Blocks(title="FlagGuard", theme=theme, css=LIQUID_GLASS_CSS) as app:
        
        user_id = gr.State("")
        user_role = gr.State("viewer")
        
        # --- LOGIN VIEW (SECURITY CONSOLE) ---
        with gr.Group(visible=True, elem_classes=["login-bg"]) as login_view:
            with gr.Row():
                with gr.Column(scale=1):
                    pass
                with gr.Column(scale=1):
                    gr.HTML("<div style='height: 10vh;'></div>")
                    
                    with gr.Group(elem_classes=["glass-card", "shimmer-border"]):
                        # Elegant Gold Logo
                        gr.HTML("""
                        <div style='text-align: center; margin-bottom: 30px;'>
                            <div class='login-logo'>🛡</div>
                            <div class='login-title'>FlagGuard</div>
                            <div class='login-subtitle'>Enterprise Feature Flag Intelligence</div>
                        </div>
                        """)
                        
                        gr.HTML("<div class='sidebar-title' style='text-align: center;'>Sign In</div>")
                        
                        email_input = gr.Textbox(
                            placeholder="ENTER USER ID",
                            show_label=False,
                            container=False
                        )
                        password_input = gr.Textbox(
                            type="password",
                            placeholder="ENTER ACCESS CODE",
                            show_label=False,
                            container=False
                        )
                        login_btn = gr.Button("→ Sign In", elem_classes=["glass-btn"])
                        login_msg = gr.Textbox(label="SYSTEM STATUS", interactive=False)
                with gr.Column(scale=1):
                    pass

        # --- DASHBOARD VIEW (COMMAND CENTER) ---
        with gr.Group(visible=False, elem_classes=["login-bg"]) as dashboard_view:
            
            # Header
            with gr.Row(elem_classes=["app-header"]):
                with gr.Column(scale=5):
                    gr.HTML("""
                    <div style='display: flex; align-items: center; gap: 16px;'>
                        <div style='width:40px; height:40px; background: linear-gradient(135deg, #d4af37, #f59e0b);
                                    border-radius:10px; display:flex; align-items:center; justify-content:center;
                                    font-size:1.2rem; box-shadow: 0 2px 12px rgba(212,175,55,0.2);'>🛡</div>
                        <div>
                            <div class='brand-text'>FlagGuard</div>
                            <div class='brand-subtitle'>
                                <span class='status-dot'></span> Operational
                            </div>
                        </div>
                    </div>
                    """)
                with gr.Column(scale=1, min_width=200):
                    role_badge = gr.HTML("<div style='text-align:right; font-family:Inter; font-size:0.75rem; color:#94a3b8;'>Role: viewer</div>")
                with gr.Column(scale=1, min_width=120):
                    logout_btn = gr.Button(
                        "Sign Out",
                        elem_classes=["glass-btn"],
                        size="sm"
                    )

            with gr.Row():
                # CONTROL PANEL (Sidebar)
                with gr.Column(scale=1, min_width=280, elem_classes=["frosted-sidebar"]):
                    gr.HTML("<div class='sidebar-section'><div class='sidebar-title'>Project</div></div>")
                    project_selector = gr.Dropdown(
                        show_label=False,
                        choices=[],
                        interactive=True
                    )
                    new_project_btn = gr.Button("+ NEW PROJECT", size="sm")
                    
                    with gr.Group(visible=False) as new_project_group:
                        new_proj_name = gr.Textbox(label="PROJECT NAME")
                        create_proj_confirm = gr.Button("CREATE")
                    
                    gr.HTML("<div style='margin: 24px 0; border-top: 1px solid rgba(212,175,55,0.1);'></div>")
                    
                    gr.HTML("<div class='sidebar-section'><div class='sidebar-title'>Analysis</div></div>")
                    
                    file_input = gr.File(label="FLAG MANIFEST", file_types=[".json", ".yaml"])
                    source_input = gr.File(label="SOURCE ARCHIVE", file_types=[".zip"])
                    
                    # AI Analysis Toggle with clear visual state
                    ai_status_html = gr.HTML("""
                    <div class='ai-toggle-container ai-toggle-on'>
                        <span style='font-family: Inter; font-weight: 600;'>AI Analysis</span>
                        <span style='font-family: Inter; font-size: 0.85rem; font-weight: 600;'>✅ Enabled</span>
                    </div>
                    """)
                    use_llm = gr.Checkbox(label="Toggle AI Analysis ON/OFF", value=True)
                    
                    analyze_btn = gr.Button("⚡ Run Analysis", elem_classes=["glass-btn"])
                    
                    gr.HTML("<div style='margin: 24px 0; border-top: 1px solid rgba(212,175,55,0.1);'></div>")
                    gr.HTML("<div class='sidebar-section'><div class='sidebar-title'>Issues</div></div>")
                    conflicts_list = gr.Textbox(show_label=False, interactive=False, lines=10)

                # MAIN DISPLAY
                with gr.Column(scale=4):
                    
                    # Diagnostic Displays (LCD Style)
                    gr.HTML("<h2 style='font-family: Outfit; color: #d4af37; text-align: center; margin-bottom: 20px; font-weight: 800;'>Overview</h2>")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                val_flags = gr.HTML("<div class='metric-value'>0</div><div class='metric-label'>Total Flags</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                val_enabled = gr.HTML("<div class='metric-value'>0</div><div class='metric-label'>Active</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                val_conflicts = gr.HTML("<div class='metric-value'>0</div><div class='metric-label'>Conflicts</div>")
                        with gr.Column(scale=1):
                            with gr.Group(elem_classes=["metric-card"]):
                                val_health = gr.HTML("<div class='metric-value'>--</div><div class='metric-label'>Health</div>")

                    gr.HTML("<div style='margin: 30px 0;'></div>")
                    
                    # Data Visualization Tabs
                    with gr.Tabs():
                        with gr.TabItem("Analytics"):
                            with gr.Row():
                                with gr.Column(scale=1):
                                    with gr.Group(elem_classes=["glass-card"]):
                                        plot_status = gr.Plot(label="Flag Status")
                                with gr.Column(scale=1):
                                    with gr.Group(elem_classes=["glass-card"]):
                                        plot_severity = gr.Plot(label="Severity")
                        
                        with gr.TabItem("Dependency Graph"):
                            with gr.Group(elem_classes=["glass-card"]):
                                graph_html = gr.HTML()
                            
                            # Full-width Mermaid Code section below graph
                            with gr.Accordion("Show Mermaid Code", open=False, elem_classes=["mermaid-code-section"]):
                                mermaid_code_display = gr.Code(
                                    label="Mermaid Graph Definition",
                                    language=None,
                                    lines=20,
                                    interactive=False,
                                )
                                with gr.Row():
                                    copy_code_btn = gr.Button(
                                        "📋 COPY CODE",
                                        elem_classes=["glass-btn"],
                                        size="sm"
                                    )

                        with gr.TabItem("Report"):
                            with gr.Group(elem_classes=["glass-card"]):
                                report_md = gr.Markdown("No scan data available.")

                        with gr.TabItem("AI Chat"):
                            create_chat_tab(app)

                        # --- ENVIRONMENTS TAB (analyst+) ---
                        with gr.TabItem("Environments") as env_tab:
                            with gr.Group(elem_classes=["glass-card"]):
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Multi-Environment Manager</div>")
                                with gr.Row():
                                    env_project_id = gr.Textbox(label="Project ID", scale=2)
                                    env_name = gr.Textbox(label="Environment Name", placeholder="e.g. dev, staging, prod", scale=2)
                                    env_create_btn = gr.Button("Create Environment", elem_classes=["glass-btn"], scale=1)
                                env_flags_json = gr.Textbox(label="Flag Overrides (JSON)", placeholder='{"dark_mode": {"enabled": true}, "new_checkout": {"enabled": false}}', lines=3)
                                env_result = gr.JSON(label="Result")

                                def create_env_action(proj_id, name, overrides_json):
                                    import json, requests
                                    try:
                                        overrides = json.loads(overrides_json) if overrides_json.strip() else {}
                                        resp = requests.post(f"http://localhost:8000/api/v1/environments/project/{proj_id}",
                                                             json={"name": name, "flag_overrides": overrides},
                                                             headers={"Authorization": "Bearer demo"})
                                        return resp.json() if resp.status_code < 400 else {"error": resp.text}
                                    except Exception as e:
                                        return {"error": str(e)}

                                env_create_btn.click(create_env_action, inputs=[env_project_id, env_name, env_flags_json], outputs=[env_result])

                                gr.HTML("<div style='margin:20px 0; border-top:1px solid rgba(212,175,55,0.1);'></div>")
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Drift Detection</div>")
                                with gr.Row():
                                    drift_env_a = gr.Textbox(label="Environment A ID", scale=1)
                                    drift_env_b = gr.Textbox(label="Environment B ID", scale=1)
                                    drift_compare_btn = gr.Button("Compare", elem_classes=["glass-btn"], scale=1)
                                drift_result = gr.JSON(label="Drift Report")

                                def compare_envs(env_a, env_b):
                                    import requests
                                    try:
                                        resp = requests.get(f"http://localhost:8000/api/v1/environments/compare",
                                                            params={"env_a_id": env_a, "env_b_id": env_b})
                                        return resp.json() if resp.status_code < 400 else {"error": resp.text}
                                    except Exception as e:
                                        return {"error": str(e)}

                                drift_compare_btn.click(compare_envs, inputs=[drift_env_a, drift_env_b], outputs=[drift_result])

                        # --- FLAG LIFECYCLE TAB (all roles can view) ---
                        with gr.TabItem("Flag Lifecycle") as lifecycle_tab:
                            with gr.Group(elem_classes=["glass-card"]):
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Flag Staleness & Zombie Detection</div>")
                                with gr.Row():
                                    lc_project_id = gr.Textbox(label="Project ID", scale=2)
                                    lc_threshold = gr.Slider(label="Stale Threshold (days)", minimum=7, maximum=180, value=30, step=1, scale=2)
                                    lc_check_btn = gr.Button("Check Lifecycle", elem_classes=["glass-btn"], scale=1)

                                with gr.Row():
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            lc_total = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Total Flags</div>")
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            lc_active = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Active</div>")
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            lc_stale = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Stale</div>")
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            lc_zombie = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Zombie</div>")

                                lc_suggestions = gr.Markdown("Run a lifecycle check to see cleanup suggestions.")
                                lc_flags_table = gr.JSON(label="Flag Details")

                                def check_lifecycle(proj_id, threshold):
                                    import requests
                                    try:
                                        resp = requests.get(f"http://localhost:8000/api/v1/lifecycle/report/{proj_id}",
                                                            params={"stale_threshold_days": int(threshold)})
                                        if resp.status_code >= 400:
                                            return ("-", "-", "-", "-", "Error fetching lifecycle data.", {})
                                        data = resp.json()
                                        h_total = f"<div class='metric-value'>{data.get('total_flags', 0)}</div><div class='metric-label'>Total Flags</div>"
                                        h_active = f"<div class='metric-value'>{data.get('active_flags', 0)}</div><div class='metric-label'>Active</div>"
                                        h_stale = f"<div class='metric-value' style='color:#f59e0b;'>{data.get('stale_flags', 0)}</div><div class='metric-label'>Stale</div>"
                                        h_zombie = f"<div class='metric-value' style='color:#ef4444;'>{data.get('zombie_flags', 0)}</div><div class='metric-label'>Zombie</div>"
                                        suggestions = "### Cleanup Suggestions\n"
                                        for s in data.get('cleanup_suggestions', []):
                                            suggestions += f"- {s}\n"
                                        return (h_total, h_active, h_stale, h_zombie, suggestions, data.get('flags', []))
                                    except Exception as e:
                                        return ("-", "-", "-", "-", f"Error: {e}", {})

                                lc_check_btn.click(check_lifecycle, inputs=[lc_project_id, lc_threshold],
                                                   outputs=[lc_total, lc_active, lc_stale, lc_zombie, lc_suggestions, lc_flags_table])

                        # --- AUDIT LOG TAB (admin only) ---
                        with gr.TabItem("Audit Log") as audit_tab:
                            with gr.Group(elem_classes=["glass-card"]):
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Audit Trail & Compliance</div>")
                                with gr.Row():
                                    audit_action_filter = gr.Dropdown(
                                        label="Filter by Action",
                                        choices=[("", ""), ("create", "create"), ("update", "update"), ("delete", "delete"), ("scan", "scan"), ("login", "login"), ("export", "export")],
                                        value="", scale=1)
                                    audit_resource_filter = gr.Dropdown(
                                        label="Filter by Resource",
                                        choices=[("", ""), ("project", "project"), ("scan", "scan"), ("webhook", "webhook"), ("environment", "environment"), ("plugin", "plugin")],
                                        value="", scale=1)
                                    audit_refresh_btn = gr.Button("Refresh", elem_classes=["glass-btn"], scale=1)
                                    audit_export_btn = gr.Button("Export CSV", elem_classes=["glass-btn"], scale=1)

                                with gr.Row():
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            audit_total = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Total Events</div>")
                                    with gr.Column(scale=1):
                                        with gr.Group(elem_classes=["metric-card"]):
                                            audit_today = gr.HTML("<div class='metric-value'>-</div><div class='metric-label'>Today</div>")

                                audit_table = gr.JSON(label="Audit Events")

                                def load_audit(action_filter, resource_filter):
                                    import requests
                                    try:
                                        params = {"limit": 50}
                                        if action_filter:
                                            params["action"] = action_filter
                                        if resource_filter:
                                            params["resource_type"] = resource_filter
                                        # Get stats
                                        stats_resp = requests.get("http://localhost:8000/api/v1/audit/stats")
                                        stats = stats_resp.json() if stats_resp.status_code < 400 else {}
                                        # Get logs
                                        logs_resp = requests.get("http://localhost:8000/api/v1/audit", params=params)
                                        logs = logs_resp.json() if logs_resp.status_code < 400 else []
                                        h_total = f"<div class='metric-value'>{stats.get('total_events', 0)}</div><div class='metric-label'>Total Events</div>"
                                        h_today = f"<div class='metric-value'>{stats.get('events_today', 0)}</div><div class='metric-label'>Today</div>"
                                        return (h_total, h_today, logs)
                                    except Exception as e:
                                        return ("-", "-", {"error": str(e)})

                                audit_refresh_btn.click(load_audit, inputs=[audit_action_filter, audit_resource_filter],
                                                       outputs=[audit_total, audit_today, audit_table])

                        # --- ADMIN PANEL (admin only) ---
                        with gr.TabItem("Admin") as admin_tab:
                            with gr.Group(elem_classes=["glass-card"]):
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>User Management</div>")
                                admin_users_btn = gr.Button("Load Users", elem_classes=["glass-btn"])
                                admin_users_table = gr.JSON(label="All Users")

                                def load_users():
                                    import requests
                                    try:
                                        resp = requests.get("http://localhost:8000/api/v1/auth/users")
                                        return resp.json() if resp.status_code < 400 else {"error": "Access denied or API not available"}
                                    except Exception as e:
                                        return {"error": str(e)}

                                admin_users_btn.click(load_users, outputs=[admin_users_table])

                                gr.HTML("<div style='margin:20px 0; border-top:1px solid rgba(212,175,55,0.1);'></div>")
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Platform Analytics</div>")
                                admin_analytics_btn = gr.Button("Load Analytics", elem_classes=["glass-btn"])
                                admin_analytics_data = gr.JSON(label="Platform Stats")
                                admin_leaderboard = gr.JSON(label="Leaderboard")

                                def load_analytics():
                                    import requests
                                    try:
                                        overview = requests.get("http://localhost:8000/api/v1/analytics/overview").json()
                                        leaderboard = requests.get("http://localhost:8000/api/v1/analytics/leaderboard").json()
                                        return (overview, leaderboard)
                                    except Exception as e:
                                        return ({"error": str(e)}, {})

                                admin_analytics_btn.click(load_analytics, outputs=[admin_analytics_data, admin_leaderboard])

                                gr.HTML("<div style='margin:20px 0; border-top:1px solid rgba(212,175,55,0.1);'></div>")
                                gr.HTML("<div class='sidebar-title' style='margin-bottom:12px;'>Plugin Management</div>")
                                admin_plugins_btn = gr.Button("Load Plugins", elem_classes=["glass-btn"])
                                admin_plugins_table = gr.JSON(label="Registered Plugins")

                                def load_plugins():
                                    import requests
                                    try:
                                        resp = requests.get("http://localhost:8000/api/v1/plugins")
                                        return resp.json() if resp.status_code < 400 else {"error": resp.text}
                                    except Exception as e:
                                        return {"error": str(e)}

                                admin_plugins_btn.click(load_plugins, outputs=[admin_plugins_table])

        # --- EVENT HANDLERS ---
        
        def perform_login(email, password):
            from flagguard.core.db import SessionLocal
            from flagguard.core.models.tables import User
            from flagguard.auth.utils import verify_password
            try:
                db = SessionLocal()
                user = db.query(User).filter(User.email == email).first()
                db.close()
                if not user or not verify_password(password, user.hashed_password):
                    return (
                        gr.update(),  # user_id
                        "viewer",     # user_role
                        "ACCESS DENIED",  # login_msg
                        gr.update(), gr.update(),  # login/dashboard views
                        gr.update(),  # role_badge
                        gr.update(), gr.update(), gr.update(),  # env, audit, admin tabs
                    )
                role = getattr(user, 'role', 'viewer') or 'viewer'
                role_colors = {'admin': '#ef4444', 'analyst': '#f59e0b', 'viewer': '#94a3b8'}
                role_color = role_colors.get(role, '#94a3b8')
                badge_html = f"<div style='text-align:right;font-family:Inter;font-size:0.8rem;'><span style='background:rgba({','.join(str(int(role_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.15);color:{role_color};padding:4px 12px;border-radius:20px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>{role}</span></div>"

                # Role-based visibility
                is_analyst_plus = role in ('admin', 'analyst')
                is_admin = role == 'admin'

                return (
                    user.id,  # user_id
                    role,     # user_role
                    "AUTHENTICATION SUCCESSFUL",  # login_msg
                    gr.update(visible=False),  # login_view
                    gr.update(visible=True),   # dashboard_view
                    badge_html,                # role_badge
                    gr.update(visible=is_analyst_plus),  # env_tab
                    gr.update(visible=is_admin),         # audit_tab
                    gr.update(visible=is_admin),         # admin_tab
                )
            except Exception as e:
                return (
                    gr.update(), "viewer", f"SYSTEM ERROR: {str(e)}",
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                )

        login_btn.click(
            perform_login,
            inputs=[email_input, password_input],
            outputs=[user_id, user_role, login_msg, login_view, dashboard_view,
                     role_badge, env_tab, audit_tab, admin_tab]
        )

        logout_btn.click(
            lambda: (gr.update(visible=True), gr.update(visible=False)),
            outputs=[login_view, dashboard_view]
        )

        # AI Analysis toggle visual feedback
        def update_ai_toggle(is_enabled):
            if is_enabled:
                return """
                <div class='ai-toggle-container ai-toggle-on'>
                    <span style='font-family: Inter; font-weight: 600;'>AI Analysis</span>
                    <span style='font-family: Inter; font-size: 0.85rem; font-weight: 600;'>✅ Enabled</span>
                </div>
                """
            else:
                return """
                <div class='ai-toggle-container ai-toggle-off'>
                    <span style='font-family: Inter; font-weight: 600;'>AI Analysis</span>
                    <span style='font-family: Inter; font-size: 0.85rem; font-weight: 600;'>⬛ Disabled</span>
                </div>
                """
        
        use_llm.change(update_ai_toggle, inputs=[use_llm], outputs=[ai_status_html])

        def refresh_projects(uid):
            if not uid:
                return gr.update(choices=[])
            from flagguard.services.project import ProjectService
            svc = ProjectService()
            projs = svc.get_projects_for_user(uid)
            return gr.update(choices=[(p.name, p.id) for p in projs], value=projs[0].id if projs else None)
        
        user_id.change(refresh_projects, inputs=[user_id], outputs=[project_selector])

        new_project_btn.click(lambda: gr.update(visible=True), outputs=[new_project_group])
        
        def create_project_action(name, uid):
            if not name:
                return gr.update(), gr.update()
            from flagguard.services.project import ProjectService
            svc = ProjectService()
            p = svc.create_project(name, uid)
            projs = svc.get_projects_for_user(uid)
            return gr.update(visible=False), gr.update(choices=[(p.name, p.id) for p in projs], value=p.id)
            
        create_proj_confirm.click(
            create_project_action,
            inputs=[new_proj_name, user_id],
            outputs=[new_project_group, project_selector]
        )

        def ui_update_wrapper(pid, config, source, use_ai):
            res = analyze_and_update_ui(config, source, use_ai)
            m_flags, m_conflicts, m_dependencies, m_enabled, m_health = res[0], res[1], res[2], res[3], res[4]
            
            h_flags = f"<div class='metric-value'>{m_flags}</div><div class='metric-label'>Total Flags</div>"
            h_en = f"<div class='metric-value'>{m_enabled}</div><div class='metric-label'>Active</div>"
            h_conf = f"<div class='metric-value'>{m_conflicts + m_dependencies}</div><div class='metric-label'>Conflicts</div>"
            h_hlt = f"<div class='metric-value'>{m_health}</div><div class='metric-label'>Health</div>"
            
            # Extract mermaid code (res[9] contains the raw mermaid code string from analyze_and_update_ui)
            mermaid_raw_code = res[9] if len(res) > 9 else "No graph data available"
            
            return (
                h_flags, h_en, h_conf, h_hlt,
                res[5], res[6], res[7], res[8], mermaid_raw_code
            )

        analyze_btn.click(
            ui_update_wrapper,
            inputs=[project_selector, file_input, source_input, use_llm],
            outputs=[
                val_flags, val_enabled, val_conflicts, val_health,
                plot_status, plot_severity,
                report_md,
                graph_html,
                mermaid_code_display
            ]
        )
        
        # Copy code to clipboard functionality
        copy_code_btn.click(
            lambda code: gr.Info("Code copied to clipboard!") or code,
            inputs=[mermaid_code_display],
            outputs=[],
            js="(code) => { navigator.clipboard.writeText(code); return code; }"
        )

    return app

def launch():
    app = create_app()
    app.launch(show_error=True, allowed_paths=["."])

if __name__ == "__main__":
    launch()
