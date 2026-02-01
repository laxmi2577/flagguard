"""FlagGuard Gradio app for Hugging Face Spaces.

Simplified version without LLM features for HF Spaces deployment.
"""

import tempfile
from pathlib import Path
from typing import Any

import gradio as gr


def analyze_flags(
    config_file: Any,
    source_zip: Any | None,
) -> tuple[str, str, str]:
    """Analyze uploaded flag configuration.
    
    Args:
        config_file: Uploaded configuration file
        source_zip: Optional ZIP of source code
        
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
        
        # Generate report
        reporter = MarkdownReporter()
        report = reporter.generate_report(flags, conflicts, [], "")
        
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


# Create Gradio interface
with gr.Blocks(
    title="FlagGuard - Feature Flag Analyzer",
    theme=gr.themes.Soft(),
) as app:
    gr.Markdown("""
# 🚩 FlagGuard
## AI Feature Flag Conflict Analyzer

Upload your feature flag configuration to detect conflicts, impossible states, and dead code.

> **Note:** LLM explanations are disabled on Hugging Face Spaces. For AI-powered insights, run FlagGuard locally with Ollama.
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
        inputs=[config_input, source_input],
        outputs=[summary_output, report_output, graph_output],
    )
    
    gr.Markdown("""
---
**Install locally:** `pip install flagguard`

[GitHub](https://github.com/yourusername/flagguard) | [PyPI](https://pypi.org/project/flagguard/)
    """)


if __name__ == "__main__":
    app.launch()
