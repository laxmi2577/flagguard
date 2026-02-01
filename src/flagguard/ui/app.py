"""Enhanced Gradio Web UI for FlagGuard.

Features:
- Interactive Dependency Graph
- Real-time Analysis Progress
- Syntax-highlighted Code Viewer
- Conflict Severity Color Coding
- Export Report as PDF
- Drag-and-Drop File Zone
- History of Past Analyses
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
import base64
import tempfile

import gradio as gr

from flagguard import __version__


# History storage path
HISTORY_FILE = Path.home() / ".flagguard" / "analysis_history.json"


# Custom CSS for enhanced styling
CUSTOM_CSS = """
/* Severity color coding */
.severity-critical { 
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 0.85em;
}
.severity-high { 
    background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 0.85em;
}
.severity-medium { 
    background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 0.85em;
}
.severity-low { 
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 0.85em;
}

/* Drag and drop zone styling */
.upload-zone {
    border: 2px dashed var(--border-color-primary) !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}
.upload-zone:hover {
    border-color: var(--primary-500) !important;
    background: var(--background-fill-secondary) !important;
}

/* History card */
.history-item {
    background: var(--background-fill-secondary);
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    cursor: pointer;
    transition: all 0.2s ease;
}
.history-item:hover {
    border-color: var(--primary-500);
    transform: translateY(-2px);
}

/* Code viewer enhancements */
.code-viewer {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 13px !important;
}

/* Conflict card styling */
.conflict-card {
    border-left: 4px solid;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
    background: var(--background-fill-secondary);
}
.conflict-critical { border-color: #dc2626; }
.conflict-high { border-color: #ea580c; }
.conflict-medium { border-color: #d97706; }
.conflict-low { border-color: #16a34a; }
"""


def load_history() -> list[dict]:
    """Load analysis history from disk."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_history(entry: dict) -> None:
    """Save a new history entry."""
    try:
        history = load_history()
        history.insert(0, entry)
        history = history[:20]  # Keep last 20 entries
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def format_history_display() -> str:
    """Format history for display."""
    history = load_history()
    if not history:
        return "*No analysis history yet*"
    
    lines = ["| Date | File | Flags | Conflicts | Status |",
             "|------|------|-------|-----------|--------|"]
    for entry in history[:10]:
        date = entry.get("date", "N/A")[:16]
        file = entry.get("config_file", "Unknown")[:20]
        flags = entry.get("flags_count", 0)
        conflicts = entry.get("conflicts_count", 0)
        status = "✅" if conflicts == 0 else "⚠️"
        lines.append(f"| {date} | {file} | {flags} | {conflicts} | {status} |")
    
    return "\n".join(lines)


def get_severity_badge(severity: str) -> str:
    """Get HTML badge for severity."""
    severity = severity.upper()
    colors = {
        "CRITICAL": ("🔴", "#dc2626"),
        "HIGH": ("🟠", "#ea580c"),
        "MEDIUM": ("🟡", "#d97706"),
        "LOW": ("🟢", "#16a34a"),
    }
    emoji, color = colors.get(severity, ("⚪", "#6b7280"))
    return f'<span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold;">{severity}</span>'


def generate_mermaid_iframe(mermaid_code: str) -> str:
    """Generate an iframe that renders Mermaid diagram."""
    encoded = base64.urlsafe_b64encode(mermaid_code.encode()).decode()
    img_url = f"https://mermaid.ink/img/{encoded}?theme=default"
    
    return f"""
    <div style="text-align: center; padding: 20px; background: #f8fafc; border-radius: 8px; min-height: 400px;">
        <img src="{img_url}" alt="Dependency Graph" style="max-width: 100%; height: auto; border-radius: 4px;" 
             onerror="this.onerror=null; this.parentElement.innerHTML='<p style=\\'color:#666;\\'>⚠️ Could not load graph. Copy the Mermaid code tab.</p>'"/>
        <p style="margin-top: 15px; color: #666; font-size: 0.9em;">
            🟢 Green = Enabled | 🔴 Red = Disabled | ⋯ Dotted = Conflict
        </p>
    </div>
    """


def generate_pdf_report(report_md: str, flags_count: int, conflicts_count: int) -> str | None:
    """Generate PDF from markdown report."""
    try:
        # Create HTML version of report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FlagGuard Analysis Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #4f46e5; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }}
        h2 {{ color: #6366f1; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #e5e7eb; padding: 12px; text-align: left; }}
        th {{ background: #f3f4f6; }}
        .critical {{ color: #dc2626; font-weight: bold; }}
        .high {{ color: #ea580c; font-weight: bold; }}
        .medium {{ color: #d97706; font-weight: bold; }}
        .low {{ color: #16a34a; font-weight: bold; }}
        code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .badge {{ background: #4f46e5; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚩 FlagGuard Analysis Report</h1>
        <span class="badge">v{__version__}</span>
    </div>
    <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p><strong>Flags Analyzed:</strong> {flags_count} | <strong>Conflicts Found:</strong> {conflicts_count}</p>
    <hr>
    {report_md}
    <hr>
    <p style="color: #6b7280; font-size: 0.9em; text-align: center;">
        Generated by FlagGuard - AI Feature Flag Conflict Analyzer
    </p>
</body>
</html>
"""
        # Save HTML file for download (PDF requires browser/wkhtmltopdf)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            return f.name
    except Exception:
        return None


def format_conflicts_with_colors(conflicts: list) -> str:
    """Format conflicts with severity color coding."""
    if not conflicts:
        return "✅ **No conflicts detected!** Your flag configuration is clean."
    
    lines = ["## Conflicts\n"]
    
    for conflict in conflicts:
        # Handle severity as enum or string
        if hasattr(conflict, 'severity'):
            sev = conflict.severity
            if hasattr(sev, 'value'):
                severity = str(sev.value).upper()
            elif hasattr(sev, 'name'):
                severity = sev.name.upper()
            else:
                severity = str(sev).upper()
        else:
            severity = "MEDIUM"
        badge = get_severity_badge(severity)
        
        flags = ", ".join(f"`{f}`" for f in conflict.flags_involved)
        
        lines.append(f"""
<div style="border-left: 4px solid {'#dc2626' if severity == 'CRITICAL' else '#ea580c' if severity == 'HIGH' else '#d97706' if severity == 'MEDIUM' else '#16a34a'}; padding: 12px 16px; margin: 12px 0; background: rgba(0,0,0,0.03); border-radius: 0 8px 8px 0;">

**{conflict.conflict_id}** {badge}

**Flags:** {flags}

**Reason:** {conflict.reason}

</div>
""")
    
    return "\n".join(lines)


def analyze_with_progress(
    config_file: Any,
    source_zip: Any | None,
    use_llm: bool,
    progress: gr.Progress = gr.Progress(),
) -> Generator[tuple[str, str, str, str, str, Any, str], None, None]:
    """Analyze with real-time progress and all outputs."""
    default_outputs = ("", "", "", "", "", None, "")
    
    if config_file is None:
        yield ("⚠️ Please upload a configuration file.", "", "", "", "", None, format_history_display())
        return
    
    try:
        # Step 1: Loading
        progress(0.1, desc="📂 Loading configuration...")
        yield ("📂 Loading configuration...", "", "", "", "", None, format_history_display())
        time.sleep(0.2)
        
        from flagguard.parsers import parse_config
        config_path = Path(config_file.name)
        config_name = config_path.name
        flags = parse_config(config_path)
        
        progress(0.3, desc=f"✓ Loaded {len(flags)} flags")
        time.sleep(0.1)
        
        # Step 2: Analysis
        progress(0.5, desc="🔍 Detecting conflicts...")
        yield (f"✓ Loaded {len(flags)} flags\n🔍 Detecting conflicts...", "", "", "", "", None, format_history_display())
        
        from flagguard.analysis import FlagSATSolver, ConflictDetector
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        progress(0.7, desc=f"✓ Found {len(conflicts)} conflicts")
        time.sleep(0.1)
        
        # Step 3: LLM (optional)
        executive_summary = ""
        if use_llm and conflicts:
            progress(0.8, desc="🤖 Generating AI explanations...")
            yield (f"✓ Loaded {len(flags)} flags\n"
                   f"✓ Found {len(conflicts)} conflicts\n"
                   f"🤖 Generating AI explanations...", "", "", "", "", None, format_history_display())
            try:
                from flagguard.llm import OllamaClient, ExplanationEngine
                client = OllamaClient()
                if client.is_available:
                    engine = ExplanationEngine(client)
                    for c in conflicts[:5]:
                        c.llm_explanation = engine.explain_conflict(c)
                    executive_summary = engine.generate_executive_summary(
                        len(flags), conflicts, []
                    )
            except Exception:
                pass
        
        # Step 4: Generate outputs
        progress(0.9, desc="📝 Generating report...")
        
        # Colored conflicts section
        colored_conflicts = format_conflicts_with_colors(conflicts)
        
        # Full markdown report
        from flagguard.reporters import MarkdownReporter
        reporter = MarkdownReporter()
        report = reporter.generate_report(flags, conflicts, [], executive_summary)
        
        # Mermaid graph
        graph_lines = ["flowchart TD"]
        for flag in flags:
            style = ":::enabled" if flag.enabled else ":::disabled"
            safe_name = flag.name.replace("-", "_").replace(".", "_")
            graph_lines.append(f'    {safe_name}["{flag.name}"]{style}')
            for dep in flag.dependencies:
                safe_dep = dep.replace("-", "_").replace(".", "_")
                graph_lines.append(f"    {safe_name} --> {safe_dep}")
        
        for conflict in conflicts:
            if len(conflict.flags_involved) >= 2:
                f1 = conflict.flags_involved[0].replace("-", "_").replace(".", "_")
                f2 = conflict.flags_involved[1].replace("-", "_").replace(".", "_")
                graph_lines.append(f"    {f1} -.->|⚠️| {f2}")
        
        graph_lines.extend([
            "",
            "    classDef enabled fill:#10b981,stroke:#059669,color:#fff",
            "    classDef disabled fill:#ef4444,stroke:#dc2626,color:#fff",
        ])
        mermaid_code = "\n".join(graph_lines)
        graph_html = generate_mermaid_iframe(mermaid_code)
        
        # Generate code viewer content (sample config)
        try:
            with open(config_path, 'r') as f:
                config_content = f.read()
        except:
            config_content = "# Could not read config file"
        
        # Generate PDF
        pdf_file = generate_pdf_report(report, len(flags), len(conflicts))
        
        # Save to history
        history_entry = {
            "date": datetime.now().isoformat(),
            "config_file": config_name,
            "flags_count": len(flags),
            "conflicts_count": len(conflicts),
        }
        save_history(history_entry)
        
        # Final summary
        progress(1.0, desc="✅ Analysis complete!")
        status = "✅ No conflicts!" if not conflicts else f"⚠️ {len(conflicts)} conflicts"
        
        summary = f"""
## 📊 Analysis Complete

| Metric | Value |
|--------|-------|
| **Status** | {status} |
| **Flags Analyzed** | {len(flags)} |
| **Conflicts Found** | {len(conflicts)} |
| **Enabled Flags** | {sum(1 for f in flags if f.enabled)} |
| **Disabled Flags** | {sum(1 for f in flags if not f.enabled)} |

{colored_conflicts}
"""
        
        yield (summary, report, graph_html, mermaid_code, config_content, pdf_file, format_history_display())
        
    except Exception as e:
        yield (f"❌ Error: {str(e)}", "", "", "", "", None, format_history_display())


def clear_history() -> str:
    """Clear all history."""
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
    except Exception:
        pass
    return "*History cleared*"


def create_app() -> gr.Blocks:
    """Create the enhanced Gradio application."""
    
    with gr.Blocks(
        title="FlagGuard - Feature Flag Analyzer",
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="purple",
        ),
        css=CUSTOM_CSS,
    ) as app:
        
        # Header
        gr.Markdown(f"""
# 🚩 FlagGuard <small style="opacity:0.7">v{__version__}</small>
### AI Feature Flag Conflict Analyzer

Detect conflicts, impossible states, and dead code in your feature flags.

---
        """)
        
        # Main content
        with gr.Row():
            # Left panel - Inputs
            with gr.Column(scale=1):
                gr.Markdown("### 📁 Upload Files")
                gr.Markdown("*Drag and drop or click to upload*")
                
                config_input = gr.File(
                    label="🗂️ Flag Configuration (JSON/YAML)",
                    file_types=[".json", ".yaml", ".yml"],
                    file_count="single",
                    elem_classes=["upload-zone"],
                )
                source_input = gr.File(
                    label="📦 Source Code (ZIP) - Optional",
                    file_types=[".zip"],
                    file_count="single",
                    elem_classes=["upload-zone"],
                )
                use_llm_checkbox = gr.Checkbox(
                    label="🤖 Use AI Explanations",
                    value=True,
                    info="Requires Ollama running locally"
                )
                
                with gr.Row():
                    analyze_btn = gr.Button(
                        "🔍 Analyze Flags",
                        variant="primary",
                        size="lg",
                        scale=2,
                    )
                    clear_btn = gr.Button(
                        "🗑️",
                        size="lg",
                        scale=1,
                    )
            
            # Right panel - Summary
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                summary_output = gr.Markdown(
                    value="*Upload a configuration file and click Analyze to begin*"
                )
        
        # Tabs for detailed output
        with gr.Tabs():
            with gr.TabItem("📋 Full Report"):
                report_output = gr.Markdown(label="Analysis Report")
                pdf_download = gr.File(
                    label="📥 Download Report (HTML)",
                    interactive=False,
                )
            
            with gr.TabItem("🔗 Dependency Graph"):
                graph_html = gr.HTML(label="Rendered Graph")
            
            with gr.TabItem("📝 Mermaid Code"):
                gr.Markdown("Copy this code to [mermaid.live](https://mermaid.live):")
                mermaid_code = gr.Code(
                    label="Mermaid Diagram",
                    language="markdown",
                    lines=12,
                )
            
            with gr.TabItem("💻 Config Viewer"):
                gr.Markdown("**Syntax-Highlighted Configuration File**")
                code_viewer = gr.Code(
                    label="Configuration Content",
                    language="json",
                    lines=20,
                    elem_classes=["code-viewer"],
                )
            
            with gr.TabItem("📜 History"):
                gr.Markdown("### Recent Analyses")
                history_display = gr.Markdown(
                    value=format_history_display(),
                )
                clear_history_btn = gr.Button("🗑️ Clear History", size="sm")
        
        # Connect handlers
        analyze_btn.click(
            fn=analyze_with_progress,
            inputs=[config_input, source_input, use_llm_checkbox],
            outputs=[summary_output, report_output, graph_html, mermaid_code, code_viewer, pdf_download, history_display],
            show_progress="full",
        )
        
        clear_btn.click(
            fn=lambda: (None, None),
            outputs=[config_input, source_input],
        )
        
        clear_history_btn.click(
            fn=clear_history,
            outputs=[history_display],
        )
        
        # Footer
        gr.Markdown("""
---
<center>

**FlagGuard** - Open Source Feature Flag Analyzer

[📚 Documentation](https://github.com/laxmi2577/flagguard) | 
[🐛 Report Issue](https://github.com/laxmi2577/flagguard/issues) | 
[⭐ Star on GitHub](https://github.com/laxmi2577/flagguard)

Made with ❤️ by Laxmi Ranjan

</center>
        """)
    
    return app


def launch(
    share: bool = False,
    server_port: int = 7860,
) -> None:
    """Launch the Gradio app."""
    app = create_app()
    app.launch(
        share=share,
        server_port=server_port,
        show_error=True,
    )


if __name__ == "__main__":
    launch()
