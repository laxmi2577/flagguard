"""Gradio Web UI for FlagGuard.

Provides a browser-based interface for analyzing feature flags.
"""

import tempfile
from pathlib import Path
from typing import Any

import gradio as gr

from flagguard import __version__


def analyze_flags(
    config_file: Any,
    source_zip: Any | None,
    use_llm: bool,
) -> tuple[str, str, str]:
    """Analyze uploaded flag configuration.
    
    Args:
        config_file: Uploaded configuration file
        source_zip: Optional ZIP of source code
        use_llm: Whether to use LLM for explanations
        
    Returns:
        Tuple of (summary, markdown_report, mermaid_graph)
    """
    if config_file is None:
        return "Please upload a configuration file.", "", ""
    
    try:
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector
        from flagguard.reporters import MarkdownReporter
        
        # Parse configuration
        config_path = Path(config_file.name)
        flags = parse_config(config_path)
        
        # Run analysis
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        # Generate summary
        status = "✅ No conflicts" if not conflicts else f"⚠️ {len(conflicts)} conflicts found"
        summary = f"""## Analysis Results

**Status:** {status}
**Flags Analyzed:** {len(flags)}
**Conflicts Found:** {len(conflicts)}
"""
        
        # Generate LLM explanations if enabled
        executive_summary = ""
        if use_llm and conflicts:
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
                pass  # LLM is optional
        
        # Generate report
        reporter = MarkdownReporter()
        report = reporter.generate_report(
            flags, conflicts, [], executive_summary
        )
        
        # Generate Mermaid graph
        graph_lines = ["flowchart TD"]
        for flag in flags:
            style = ":::enabled" if flag.enabled else ":::disabled"
            graph_lines.append(f"    {flag.name}[{flag.name}]{style}")
            for dep in flag.dependencies:
                graph_lines.append(f"    {flag.name} --> {dep}")
        graph_lines.extend([
            "",
            "    classDef enabled fill:#90EE90",
            "    classDef disabled fill:#FFB6C1",
        ])
        mermaid = "\n".join(graph_lines)
        
        return summary, report, mermaid
        
    except Exception as e:
        return f"Error: {str(e)}", "", ""


def create_app() -> gr.Blocks:
    """Create the Gradio application.
    
    Returns:
        Configured Gradio Blocks application
    """
    with gr.Blocks(
        title="FlagGuard - Feature Flag Analyzer",
        theme=gr.themes.Soft(),
    ) as app:
        gr.Markdown(f"""
# 🚩 FlagGuard
## AI Feature Flag Conflict Analyzer v{__version__}

Upload your feature flag configuration to detect conflicts, impossible states, and dead code.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                config_input = gr.File(
                    label="Flag Configuration (JSON/YAML)",
                    file_types=[".json", ".yaml", ".yml"],
                )
                source_input = gr.File(
                    label="Source Code (ZIP) - Optional",
                    file_types=[".zip"],
                )
                use_llm_checkbox = gr.Checkbox(
                    label="Use AI Explanations (requires Ollama)",
                    value=True,
                )
                analyze_btn = gr.Button("🔍 Analyze", variant="primary")
            
            with gr.Column(scale=2):
                summary_output = gr.Markdown(label="Summary")
        
        with gr.Tabs():
            with gr.TabItem("📋 Report"):
                report_output = gr.Markdown(label="Full Report")
            
            with gr.TabItem("🔗 Dependency Graph"):
                graph_output = gr.Textbox(
                    label="Mermaid Diagram (Copy to mermaid.live)",
                    lines=15,
                )
        
        analyze_btn.click(
            fn=analyze_flags,
            inputs=[config_input, source_input, use_llm_checkbox],
            outputs=[summary_output, report_output, graph_output],
        )
        
        gr.Markdown("""
---
**Examples:** [LaunchDarkly](https://launchdarkly.com) | [Unleash](https://getunleash.io)

Made with ❤️ by the FlagGuard team
        """)
    
    return app


def launch(
    share: bool = False,
    server_port: int = 7860,
) -> None:
    """Launch the Gradio app.
    
    Args:
        share: Whether to create a public link
        server_port: Port to run the server on
    """
    app = create_app()
    app.launch(
        share=share,
        server_port=server_port,
        show_error=True,
    )


if __name__ == "__main__":
    launch()
