"""Shared analysis logic and helpers for FlagGuard UI.

Also contains the FIXED Mermaid dependency graph generator.
Bug fix: Mermaid code with braces was breaking Python f-string HTML templates.
"""

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

import gradio as gr

HISTORY_FILE = Path.home() / ".flagguard" / "scan_history.json"

def create_charts(flags: list, conflicts: list):
    """Generate Gold/Emerald/Silver palette charts."""
    if not PLOTLY_AVAILABLE:
        return None, None

    enabled_count = sum(1 for f in flags if f.enabled)
    disabled_count = len(flags) - enabled_count
    total = len(flags)

    # Donut gauge
    fig1 = go.Figure(data=[go.Pie(
        labels=['Active', 'Inactive'],
        values=[enabled_count if enabled_count else 0, disabled_count if disabled_count else 1],
        hole=.75,
        marker_colors=['#d4af37', '#333333'],
        textinfo='none',
        hoverinfo='label+value',
        showlegend=False
    )])
    fig1.add_annotation(text=f"<b>{total}</b>", x=0.5, y=0.55, font_size=48,
                        font_color="#d4af37", showarrow=False)
    fig1.add_annotation(text="TOTAL FLAGS", x=0.5, y=0.4, font_size=12,
                        font_color="#94a3b8", showarrow=False)
    fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       margin=dict(t=20, b=20, l=20, r=20), height=280,
                       font=dict(family="Outfit"))

    # Severity bar
    from flagguard.analysis import ConflictType
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
    f_labels, f_counts, f_colors = zip(*filtered_data)

    fig2 = go.Figure(data=[go.Bar(
        x=f_labels, y=f_counts,
        marker=dict(color=list(f_colors), line=dict(color='#1a1a1a', width=2)),
        text=f_counts, textposition='outside',
        textfont=dict(color='#d4af37', size=14, family='JetBrains Mono')
    )])
    fig2.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(26,26,26,0.3)',
        font=dict(family="Outfit", color="#94a3b8"),
        margin=dict(t=40, b=40, l=40, r=40), height=280,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(212,175,55,0.1)', zeroline=False),
        title=dict(text="Conflict Severity", font=dict(size=14, color='#d4af37'), x=0.5, xanchor='center')
    )
    return fig1, fig2

def generate_mermaid_html(flags: list, conflicts: list) -> tuple[str, str]:
    """
    Generate dependency graph HTML with Mermaid.
    FIXED BUG: Mermaid code is injected as a JS string (json.dumps) to avoid
    Python f-string brace escaping issues that corrupted the previous HTML.
    """
    from flagguard.analysis import ConflictType

    graph_lines = ["flowchart TD"]
    for f in flags:
        style = ":::active" if f.enabled else ":::inactive"
        name = f.name.replace("-", "_").replace(".", "_")
        label = f.name.replace('"', "'")
        graph_lines.append(f'    {name}["{label}"]{style}')
        for dep in f.dependencies:
            dep_name = dep.replace("-", "_").replace(".", "_")
            graph_lines.append(f"    {name} -->|REQUIRES| {dep_name}")

    for c in conflicts:
        if len(c.flags_involved) >= 2:
            f1 = c.flags_involved[0].replace("-", "_").replace(".", "_")
            f2 = c.flags_involved[1].replace("-", "_").replace(".", "_")
            if c.conflict_type == ConflictType.MUTUAL_EXCLUSION:
                graph_lines.append(f"    {f1} x--x {f2}")
                graph_lines.append(f"    {f1}:::conflict")
                graph_lines.append(f"    {f2}:::conflict")
            elif c.conflict_type == ConflictType.DEPENDENCY_VIOLATION:
                graph_lines.append(f"    {f1} ==>|MISSING| {f2}")
                graph_lines.append(f"    {f1}:::violation")

    graph_lines.append("    classDef active fill:#d4af37,stroke:#b8962f,stroke-width:3px,color:#000,font-weight:bold")
    graph_lines.append("    classDef inactive fill:#333333,stroke:#555555,stroke-width:2px,color:#94a3b8")
    graph_lines.append("    classDef conflict fill:#dc2626,stroke:#991b1b,stroke-width:3px,color:#fff,font-weight:bold")
    graph_lines.append("    classDef violation fill:#f59e0b,stroke:#d4af37,stroke-width:3px,color:#000,font-weight:bold")

    mermaid_code = "\n".join(graph_lines)

    # KEY FIX: Use json.dumps() to safely embed the mermaid string in JS
    # This avoids Python f-string brace collision AND properly escapes special chars
    mermaid_js_string = json.dumps(mermaid_code)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700&family=JetBrains+Mono:wght@400&display=swap');
body {{
    margin: 0;
    background: linear-gradient(135deg, rgba(10,25,41,0.95) 0%, rgba(30,58,95,0.95) 100%);
    font-family: 'JetBrains Mono', monospace;
    overflow: hidden;
}}
#container {{
    width: 100%; height: 700px;
    display: flex; flex-direction: column;
    padding: 16px; box-sizing: border-box;
}}
.graph-header {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(212,175,55,0.2);
    border-radius: 8px; padding: 10px 16px;
    margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
}}
.graph-title {{
    font-family: 'Outfit', sans-serif; font-size: 1rem;
    font-weight: 700; color: #d4af37;
}}
.legend {{ display: flex; gap: 12px; font-size: 0.7rem; color: #94a3b8; align-items: center; }}
.dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 4px; }}
.graph-panel {{
    flex: 1; background: rgba(14,25,41,0.8);
    border: 1px solid rgba(212,175,55,0.15); border-radius: 12px;
    padding: 12px; overflow: auto; position: relative;
}}
#graph-content {{ width: 100%; height: 100%; min-height: 500px; }}
.error-msg {{ color: #ef4444; text-align: center; padding: 40px; font-family: Outfit; }}
</style>
</head>
<body>
<div id="container">
    <div class="graph-header">
        <div class="graph-title">Dependency Graph</div>
        <div class="legend">
            <span><span class="dot" style="background:#d4af37"></span>Active</span>
            <span><span class="dot" style="background:#333"></span>Inactive</span>
            <span><span class="dot" style="background:#dc2626"></span>Conflict</span>
            <span><span class="dot" style="background:#f59e0b"></span>Violation</span>
        </div>
    </div>
    <div class="graph-panel">
        <div id="graph-content"></div>
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
            primaryColor: '#d4af37',
            primaryTextColor: '#000',
            primaryBorderColor: '#b8962f',
            lineColor: '#94a3b8',
            secondaryColor: '#1e3a5f',
            tertiaryColor: '#152940'
        }},
        flowchart: {{ htmlLabels: true, curve: 'basis', padding: 20 }}
    }});

    // THE FIX: inject mermaid code via JS variable (no Python f-string brace conflicts)
    const mermaidCode = {mermaid_js_string};
    const container = document.getElementById('graph-content');

    try {{
        const {{ svg }} = await mermaid.render('graph-svg', mermaidCode);
        container.innerHTML = svg;
        // Make SVG responsive
        const svgEl = container.querySelector('svg');
        if (svgEl) {{
            svgEl.style.width = '100%';
            svgEl.style.height = 'auto';
            svgEl.style.maxHeight = '560px';
        }}
    }} catch (err) {{
        container.innerHTML = '<div class="error-msg">Graph error: ' + err.message + '<br/><small>Check Mermaid code in the Report tab</small></div>';
    }}
</script>
</body>
</html>"""

    encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    iframe = f'<iframe src="data:text/html;base64,{encoded}" style="width:100%; height:620px; border:none; border-radius:12px;"></iframe>'
    return iframe, mermaid_code

def load_history() -> list[dict]:
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_history_entry(entry: dict):
    try:
        history = load_history()
        history.insert(0, entry)
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[:50], f)
    except Exception:
        pass

def run_analysis(config_file, source_file, use_llm, progress=gr.Progress()):
    """Core analysis logic — shared by all role dashboards."""
    if not config_file:
        return [0, 0, 0, 0, "0%", None, None, "No scan data.", "", ""]

    try:
        progress(0.1, desc="Initializing...")
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector, ConflictType
        from flagguard.reporters import MarkdownReporter

        flags = parse_config(Path(config_file.name))

        progress(0.4, desc="Scanning Dependencies...")
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()

        from flagguard.analysis import ConflictType
        mutual_exclusions = [c for c in conflicts if c.conflict_type == ConflictType.MUTUAL_EXCLUSION]
        dependency_violations = [c for c in conflicts if c.conflict_type == ConflictType.DEPENDENCY_VIOLATION]

        summary = ""
        if use_llm and conflicts:
            progress(0.6, desc="AI Analysis...")
            try:
                from flagguard.llm import OllamaClient, ExplanationEngine
                client = OllamaClient()
                if client.is_available:
                    engine = ExplanationEngine(client)
                    for c in conflicts[:5]:
                        c.llm_explanation = engine.explain_conflict(c)
                    summary = engine.generate_executive_summary(len(flags), conflicts, [])
            except Exception:
                pass

        progress(0.8, desc="Generating Report...")

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

        iframe_html, mermaid_code = generate_mermaid_html(flags, conflicts)

        save_history_entry({
            "date": datetime.now().isoformat(),
            "config_file": Path(config_file.name).name,
            "flags_count": m_flags,
            "conflicts_count": len(conflicts)
        })

        return (m_flags, m_conflicts, m_dependencies, m_enabled, m_health,
                fig1, fig2, report_md, iframe_html, mermaid_code)

    except Exception as e:
        raise gr.Error(f"Analysis Error: {str(e)}")

def format_conflicts_list(conflicts) -> str:
    if not conflicts:
        return "No conflicts detected."
    lines = []
    for c in conflicts:
        flags_str = " vs ".join(c.flags_involved[:2])
        lines.append(f"[{c.conflict_type.value.upper()}] {flags_str}")
    return "\n".join(lines)

def get_user_notifications(user_id: str) -> tuple[int, list]:
    """Fetch unread notification count and list for a user."""
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import Notification
        db = SessionLocal()
        notifs = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        result = [{"id": n.id, "title": n.title, "message": n.message, "type": n.type}
                  for n in notifs]
        count = len(result)

        return count, result
    except Exception:
        return 0, []
