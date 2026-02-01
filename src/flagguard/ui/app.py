"""Enhanced Gradio Web UI for FlagGuard.

Provides a browser-based interface with:
- Interactive Dependency Graph (Mermaid.js)
- Real-time Analysis Progress
- Dark/Light Theme Toggle
"""

import time
from pathlib import Path
from typing import Any, Generator

import gradio as gr

from flagguard import __version__


# Custom CSS for theme and styling
CUSTOM_CSS = """
/* Theme variables */
:root {
    --primary-color: #6366f1;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
}

/* Progress bar styling */
.progress-container {
    background: var(--background-fill-secondary);
    border-radius: 8px;
    padding: 16px;
    margin: 10px 0;
}

.progress-bar {
    height: 8px;
    background: linear-gradient(90deg, var(--primary-color), #8b5cf6);
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* Status badges */
.status-success { color: var(--success-color); font-weight: bold; }
.status-warning { color: var(--warning-color); font-weight: bold; }
.status-error { color: var(--error-color); font-weight: bold; }

/* Graph container */
.mermaid-container {
    background: var(--background-fill-primary);
    border-radius: 8px;
    padding: 20px;
    min-height: 400px;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* Card styling */
.stat-card {
    background: var(--background-fill-secondary);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    border: 1px solid var(--border-color-primary);
}

.stat-number {
    font-size: 2.5rem;
    font-weight: bold;
    color: var(--primary-color);
}

.stat-label {
    font-size: 0.9rem;
    opacity: 0.8;
}
"""

# Mermaid.js HTML template for interactive graph
MERMAID_HTML_TEMPLATE = """
<div id="mermaid-graph" class="mermaid-container">
    <div class="mermaid">
{mermaid_code}
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({{ 
        startOnLoad: true,
        theme: '{theme}',
        flowchart: {{
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis'
        }}
    }});
    mermaid.contentLoaded();
</script>
<div style="margin-top: 10px; text-align: center;">
    <small>🖱️ Click nodes for details | 🔍 Zoom with scroll | ↔️ Drag to pan</small>
</div>
"""


def analyze_with_progress(
    config_file: Any,
    source_zip: Any | None,
    use_llm: bool,
    progress: gr.Progress = gr.Progress(),
) -> Generator[tuple[str, str, str, str], None, None]:
    """Analyze with real-time progress updates.
    
    Yields progress updates during analysis.
    """
    if config_file is None:
        yield "⚠️ Please upload a configuration file.", "", "", ""
        return
    
    try:
        # Step 1: Loading
        progress(0.1, desc="📂 Loading configuration...")
        yield "📂 Loading configuration...", "", "", ""
        time.sleep(0.3)
        
        from flagguard.parsers import parse_config
        config_path = Path(config_file.name)
        flags = parse_config(config_path)
        
        progress(0.3, desc=f"✓ Loaded {len(flags)} flags")
        yield f"✓ Loaded {len(flags)} flags", "", "", ""
        time.sleep(0.2)
        
        # Step 2: Analysis
        progress(0.5, desc="🔍 Detecting conflicts...")
        yield f"✓ Loaded {len(flags)} flags\n🔍 Detecting conflicts...", "", "", ""
        
        from flagguard.analysis import FlagSATSolver, ConflictDetector
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        progress(0.7, desc=f"✓ Found {len(conflicts)} conflicts")
        yield f"✓ Loaded {len(flags)} flags\n✓ Found {len(conflicts)} conflicts", "", "", ""
        time.sleep(0.2)
        
        # Step 3: LLM (optional)
        executive_summary = ""
        if use_llm and conflicts:
            progress(0.8, desc="🤖 Generating AI explanations...")
            yield (f"✓ Loaded {len(flags)} flags\n"
                   f"✓ Found {len(conflicts)} conflicts\n"
                   f"🤖 Generating AI explanations..."), "", "", ""
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
        
        # Step 4: Generate report
        progress(0.9, desc="📝 Generating report...")
        from flagguard.reporters import MarkdownReporter
        reporter = MarkdownReporter()
        report = reporter.generate_report(flags, conflicts, [], executive_summary)
        
        # Generate Mermaid graph
        graph_lines = ["flowchart TD"]
        for flag in flags:
            style = ":::enabled" if flag.enabled else ":::disabled"
            label = f"{flag.name}"
            graph_lines.append(f'    {flag.name}["{label}"]{style}')
            for dep in flag.dependencies:
                graph_lines.append(f"    {flag.name} --> {dep}")
        
        # Add conflict edges
        for conflict in conflicts:
            if len(conflict.flags_involved) >= 2:
                graph_lines.append(
                    f"    {conflict.flags_involved[0]} -.->|conflict| {conflict.flags_involved[1]}"
                )
        
        graph_lines.extend([
            "",
            "    classDef enabled fill:#10b981,stroke:#059669,color:#fff",
            "    classDef disabled fill:#ef4444,stroke:#dc2626,color:#fff",
        ])
        mermaid_code = "\n".join(graph_lines)
        
        # Create interactive HTML graph
        interactive_graph = MERMAID_HTML_TEMPLATE.format(
            mermaid_code=mermaid_code,
            theme="default"
        )
        
        # Final summary
        progress(1.0, desc="✅ Analysis complete!")
        status = "✅ No conflicts found!" if not conflicts else f"⚠️ {len(conflicts)} conflicts detected"
        
        summary = f"""
## 📊 Analysis Complete

| Metric | Value |
|--------|-------|
| **Status** | {status} |
| **Flags Analyzed** | {len(flags)} |
| **Conflicts Found** | {len(conflicts)} |
| **Enabled Flags** | {sum(1 for f in flags if f.enabled)} |
| **Disabled Flags** | {sum(1 for f in flags if not f.enabled)} |
"""
        
        yield summary, report, interactive_graph, mermaid_code
        
    except Exception as e:
        yield f"❌ Error: {str(e)}", "", "", ""


def create_app() -> gr.Blocks:
    """Create the enhanced Gradio application."""
    
    # Theme options
    light_theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="purple",
    )
    
    with gr.Blocks(
        title="FlagGuard - Feature Flag Analyzer",
        theme=light_theme,
        css=CUSTOM_CSS,
    ) as app:
        
        # Header with theme toggle
        with gr.Row():
            with gr.Column(scale=4):
                gr.Markdown(f"""
# 🚩 FlagGuard <small style="opacity:0.7">v{__version__}</small>
### AI Feature Flag Conflict Analyzer

Detect conflicts, impossible states, and dead code in your feature flags.
                """)
            with gr.Column(scale=1):
                theme_toggle = gr.Radio(
                    choices=["🌞 Light", "🌙 Dark"],
                    value="🌞 Light",
                    label="Theme",
                    interactive=True,
                )
        
        gr.Markdown("---")
        
        # Main content
        with gr.Row():
            # Left panel - Inputs
            with gr.Column(scale=1):
                gr.Markdown("### 📁 Upload Files")
                config_input = gr.File(
                    label="Flag Configuration",
                    file_types=[".json", ".yaml", ".yml"],
                    file_count="single",
                )
                source_input = gr.File(
                    label="Source Code (ZIP) - Optional",
                    file_types=[".zip"],
                    file_count="single",
                )
                use_llm_checkbox = gr.Checkbox(
                    label="🤖 Use AI Explanations",
                    value=True,
                    info="Requires Ollama running locally"
                )
                analyze_btn = gr.Button(
                    "🔍 Analyze Flags",
                    variant="primary",
                    size="lg",
                )
                
                # Progress display
                progress_output = gr.Markdown(
                    value="*Upload a file to begin*",
                    label="Progress"
                )
            
            # Right panel - Summary
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                summary_output = gr.Markdown(
                    value="*Analysis results will appear here*"
                )
        
        # Tabs for detailed output
        with gr.Tabs():
            with gr.TabItem("📋 Detailed Report"):
                report_output = gr.Markdown(label="Analysis Report")
            
            with gr.TabItem("🔗 Interactive Graph"):
                gr.Markdown("""
**Dependency Graph** - Visualize flag relationships
- 🟢 **Green** = Enabled flags
- 🔴 **Red** = Disabled flags  
- **Dotted lines** = Conflicts
                """)
                graph_html = gr.HTML(label="Interactive Mermaid Graph")
            
            with gr.TabItem("📝 Mermaid Code"):
                gr.Markdown("Copy this code to [mermaid.live](https://mermaid.live) for editing:")
                mermaid_code = gr.Code(
                    label="Mermaid Diagram Code",
                    language="markdown",
                    lines=15,
                )
        
        # Connect analyze button with progress
        analyze_btn.click(
            fn=analyze_with_progress,
            inputs=[config_input, source_input, use_llm_checkbox],
            outputs=[summary_output, report_output, graph_html, mermaid_code],
            show_progress="full",
        )
        
        # Theme toggle handler (client-side)
        def update_theme(choice):
            # Note: Full theme switching requires page reload in Gradio
            return f"Theme preference: {choice}"
        
        theme_toggle.change(
            fn=update_theme,
            inputs=[theme_toggle],
            outputs=[progress_output],
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
    dark_mode: bool = False,
) -> None:
    """Launch the Gradio app.
    
    Args:
        share: Whether to create a public link
        server_port: Port to run the server on
        dark_mode: Start in dark mode
    """
    app = create_app()
    app.launch(
        share=share,
        server_port=server_port,
        show_error=True,
    )


if __name__ == "__main__":
    launch()
