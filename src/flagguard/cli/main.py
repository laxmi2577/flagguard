"""FlagGuard CLI - Command-line interface for flag analysis."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from flagguard import __version__
from flagguard.core.logging import setup_logging


console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="flagguard")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool) -> None:
    """FlagGuard - AI Feature Flag Conflict Analyzer.
    
    Detect conflicts, impossible states, and dead code in your
    feature flag configurations.
    """
    if debug:
        setup_logging("DEBUG")
    else:
        setup_logging("INFO")


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to flag configuration file (JSON/YAML)",
)
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to source code directory",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)",
)
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "json", "text"]),
    default="text",
    help="Output format",
)
@click.option(
    "--use-llm/--no-llm",
    default=True,
    help="Use LLM for explanations",
)
def analyze(
    config: Path,
    source: Path,
    output: Optional[Path],
    format: str,
    use_llm: bool,
) -> None:
    """Analyze feature flags for conflicts and dead code.
    
    Examples:
    
        flagguard analyze --config flags.json --source ./src
        
        flagguard analyze -c config.yaml -s ./src -f markdown -o report.md
    """
    console.print(Panel.fit(
        "[bold blue]FlagGuard Analysis[/bold blue]",
        subtitle=f"v{__version__}",
    ))
    
    with console.status("[bold green]Loading configuration..."):
        from flagguard.parsers import parse_config
        flags = parse_config(config)
        console.print(f"✓ Loaded {len(flags)} flags from {config.name}")
    
    with console.status("[bold green]Scanning source code..."):
        from flagguard.parsers.ast import SourceScanner
        scanner = SourceScanner()
        usages = scanner.scan_directory(source)
        console.print(
            f"✓ Scanned {usages.files_scanned} files, "
            f"found {len(usages.usages)} flag usages"
        )
    
    with console.status("[bold green]Detecting conflicts..."):
        from flagguard.analysis import FlagSATSolver, ConflictDetector, DeadCodeFinder
        
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        dead_finder = DeadCodeFinder(solver)
        dead_blocks = dead_finder.find_dead_code(usages.usages)
        
        console.print(f"✓ Found {len(conflicts)} conflicts, {len(dead_blocks)} dead code blocks")
    
    # Generate explanations if LLM enabled
    executive_summary = ""
    if use_llm:
        with console.status("[bold green]Generating explanations..."):
            from flagguard.llm import OllamaClient, ExplanationEngine
            
            client = OllamaClient()
            engine = ExplanationEngine(client, use_llm=client.is_available)
            
            for conflict in conflicts[:10]:
                conflict.llm_explanation = engine.explain_conflict(conflict)
            
            executive_summary = engine.generate_executive_summary(
                len(flags), conflicts, dead_blocks
            )
    
    # Generate output
    if format == "json":
        from flagguard.reporters import JSONReporter
        reporter = JSONReporter()
        report = reporter.generate_report(flags, conflicts, dead_blocks, executive_summary)
        report_text = reporter.to_string(report)
    elif format == "markdown":
        from flagguard.reporters import MarkdownReporter
        reporter = MarkdownReporter()
        report_text = reporter.generate_report(
            flags, conflicts, dead_blocks, executive_summary
        )
    else:
        report_text = _format_text_output(flags, conflicts, dead_blocks, executive_summary)
    
    if output:
        output.write_text(report_text, encoding="utf-8")
        console.print(f"\n✓ Report saved to {output}")
    else:
        console.print("\n" + report_text)
    
    # Exit with error if conflicts found
    if conflicts:
        raise SystemExit(1)


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to flag configuration file",
)
def parse(config: Path) -> None:
    """Parse and display flag configuration.
    
    Useful for validating configuration files.
    """
    from flagguard.parsers import parse_config
    
    flags = parse_config(config)
    
    table = Table(title=f"Flags in {config.name}")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Enabled", style="green")
    table.add_column("Dependencies")
    
    for flag in flags:
        enabled = "✓" if flag.enabled else "✗"
        deps = ", ".join(flag.dependencies) if flag.dependencies else "-"
        table.add_row(flag.name, flag.flag_type.value, enabled, deps)
    
    console.print(table)


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to flag configuration file",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output file for Mermaid diagram",
)
def graph(config: Path, output: Optional[Path]) -> None:
    """Generate dependency graph as Mermaid diagram."""
    from flagguard.parsers import parse_config
    
    flags = parse_config(config)
    
    # Generate Mermaid diagram
    lines = ["flowchart TD"]
    
    for flag in flags:
        # Add node
        style = ":::enabled" if flag.enabled else ":::disabled"
        lines.append(f"    {flag.name}[{flag.name}]{style}")
        
        # Add edges for dependencies
        for dep in flag.dependencies:
            lines.append(f"    {flag.name} --> {dep}")
    
    # Add styles
    lines.extend([
        "",
        "    classDef enabled fill:#90EE90",
        "    classDef disabled fill:#FFB6C1",
    ])
    
    mermaid = "\n".join(lines)
    
    if output:
        output.write_text(mermaid, encoding="utf-8")
        console.print(f"✓ Graph saved to {output}")
    else:
        console.print("```mermaid")
        console.print(mermaid)
        console.print("```")


@cli.command("check-llm")
def check_llm() -> None:
    """Check LLM (Ollama) availability."""
    from flagguard.llm import OllamaClient, LLMConfig
    
    config = LLMConfig()
    client = OllamaClient(config)
    
    if client.is_available:
        console.print("[green]✓ Ollama is available[/green]")
        
        if client.check_model_available():
            console.print(f"[green]✓ Model '{config.model}' is available[/green]")
        else:
            console.print(f"[yellow]⚠ Model '{config.model}' not found[/yellow]")
            console.print(f"  Run: ollama pull {config.model}")
    else:
        console.print("[red]✗ Ollama is not available[/red]")
        console.print("  Install from: https://ollama.ai")


def _format_text_output(
    flags: list,
    conflicts: list,
    dead_blocks: list,
    summary: str,
) -> str:
    """Format output as plain text."""
    lines = [
        "=" * 60,
        "FLAGGUARD ANALYSIS REPORT",
        "=" * 60,
        "",
        f"Flags analyzed: {len(flags)}",
        f"Conflicts found: {len(conflicts)}",
        f"Dead code blocks: {len(dead_blocks)}",
        "",
    ]
    
    if summary:
        lines.extend(["SUMMARY:", summary, ""])
    
    if conflicts:
        lines.append("CONFLICTS:")
        for c in conflicts:
            lines.append(f"  [{c.severity.value.upper()}] {c.conflict_id}: {c.reason}")
        lines.append("")
    
    if dead_blocks:
        lines.append("DEAD CODE:")
        for b in dead_blocks:
            lines.append(f"  {b.file_path}:{b.start_line}-{b.end_line} ({b.estimated_lines} lines)")
    
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
