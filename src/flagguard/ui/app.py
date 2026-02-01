"""Enhanced Gradio Web UI for FlagGuard.

Provides a browser-based interface with:
- Interactive Dependency Graph (rendered Mermaid via iframe)
- Real-time Analysis Progress
"""

import time
from pathlib import Path
from typing import Any, Generator
import base64

import gradio as gr

from flagguard import __version__


# Custom CSS for styling
CUSTOM_CSS = """
/* Status badges */
.status-success { color: #10b981; font-weight: bold; }
.status-warning { color: #f59e0b; font-weight: bold; }
.status-error { color: #ef4444; font-weight: bold; }

/* Graph container */
.graph-frame {
    width: 100%;
    height: 500px;
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    background: white;
}
"""


def generate_mermaid_iframe(mermaid_code: str) -> str:
    """Generate an iframe that renders Mermaid diagram using mermaid.ink service."""
    # Encode mermaid code for URL
    encoded = base64.urlsafe_b64encode(mermaid_code.encode()).decode()
    
    # Use mermaid.ink to render the diagram
    img_url = f"https://mermaid.ink/img/{encoded}?theme=default"
    
    html = f"""
    <div style="text-align: center; padding: 20px; background: #f8fafc; border-radius: 8px; min-height: 400px;">
        <img src="{img_url}" alt="Dependency Graph" style="max-width: 100%; height: auto; border-radius: 4px;" 
             onerror="this.onerror=null; this.parentElement.innerHTML='<p style=\\'color:#666;\\'>⚠️ Could not load graph. Copy the Mermaid code and paste it at <a href=\\'https://mermaid.live\\' target=\\'_blank\\'>mermaid.live</a></p>'"/>
        <p style="margin-top: 15px; color: #666; font-size: 0.9em;">
            🟢 Green = Enabled | 🔴 Red = Disabled | ⋯ Dotted = Conflict
        </p>
    </div>
    """
    return html


def analyze_with_progress(
    config_file: Any,
    source_zip: Any | None,
    use_llm: bool,
    progress: gr.Progress = gr.Progress(),
) -> Generator[tuple[str, str, str, str], None, None]:
    """Analyze with real-time progress updates."""
    if config_file is None:
        yield "⚠️ Please upload a configuration file.", "", "", ""
        return
    
    try:
        # Step 1: Loading
        progress(0.1, desc="📂 Loading configuration...")
        yield "📂 Loading configuration...", "", "", ""
        time.sleep(0.2)
        
        from flagguard.parsers import parse_config
        config_path = Path(config_file.name)
        flags = parse_config(config_path)
        
        progress(0.3, desc=f"✓ Loaded {len(flags)} flags")
        yield f"✓ Loaded {len(flags)} flags", "", "", ""
        time.sleep(0.1)
        
        # Step 2: Analysis
        progress(0.5, desc="🔍 Detecting conflicts...")
        yield f"✓ Loaded {len(flags)} flags\n🔍 Detecting conflicts...", "", "", ""
        
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
            # Sanitize flag name for Mermaid
            safe_name = flag.name.replace("-", "_").replace(".", "_")
            label = flag.name
            graph_lines.append(f'    {safe_name}["{label}"]{style}')
            for dep in flag.dependencies:
                safe_dep = dep.replace("-", "_").replace(".", "_")
                graph_lines.append(f"    {safe_name} --> {safe_dep}")
        
        # Add conflict edges
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
        
        # Create rendered graph HTML
        graph_html = generate_mermaid_iframe(mermaid_code)
        
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
        
        yield summary, report, graph_html, mermaid_code
        
    except Exception as e:
        yield f"❌ Error: {str(e)}", "", "", ""


def create_app() -> gr.Blocks:
    """Create the Gradio application."""
    
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
            
            # Right panel - Summary
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                summary_output = gr.Markdown(
                    value="*Upload a configuration file and click Analyze to begin*"
                )
        
        # Tabs for detailed output
        with gr.Tabs():
            with gr.TabItem("📋 Detailed Report"):
                report_output = gr.Markdown(label="Analysis Report")
            
            with gr.TabItem("🔗 Dependency Graph"):
                gr.Markdown("""
**Visual Dependency Graph** - Shows relationships between flags
                """)
                graph_html = gr.HTML(label="Rendered Graph")
            
            with gr.TabItem("📝 Mermaid Code"):
                gr.Markdown("Copy this code to [mermaid.live](https://mermaid.live) for editing:")
                mermaid_code = gr.Code(
                    label="Mermaid Diagram Code",
                    language="markdown",
                    lines=15,
                )
        
        # Connect analyze button
        analyze_btn.click(
            fn=analyze_with_progress,
            inputs=[config_input, source_input, use_llm_checkbox],
            outputs=[summary_output, report_output, graph_html, mermaid_code],
            show_progress="full",
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
