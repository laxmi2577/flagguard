"""FlagGuard CLI - Command-line interface for flag analysis."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from flagguard import __version__
from flagguard.core.logging import setup_logging


console = Console(stderr=True, force_terminal=False)


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
        import sys
        # Print report to stdout (while console logs go to stderr)
        # This ensures clean JSON output for tools
        sys.stdout.write("\n" + report_text + "\n")
    
    # Exit with error if conflicts found (unless outputting JSON which contains status)
    if conflicts and format != "json":
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


@cli.command()
def init() -> None:
    """Initialize FlagGuard in current directory.
    
    Creates a .flagguard.yaml configuration file with sensible defaults.
    
    Example:
        flagguard init
    """
    config_content = """# FlagGuard Configuration
# This file configures FlagGuard for your project.

# Format of your flag configuration files
config_format: auto  # auto, launchdarkly, unleash, generic

# Paths to scan for source code
source_paths:
  - ./src
  - ./app

# Patterns to exclude from scanning
exclude_patterns:
  - node_modules
  - .venv
  - __pycache__
  - "*.test.*"
  - "*.spec.*"
  - dist
  - build

# LLM configuration for AI-powered explanations
llm:
  enabled: true
  model: gemma2:2b
  host: http://localhost:11434
  temperature: 0.3

# Analysis settings
analysis:
  max_flags: 100
  max_conflicts: 100
  detect_dead_code: true
  detect_cycles: true

# Reporting options
reporting:
  format: markdown
  include_executive_summary: true
  include_dependency_graph: true
"""
    
    config_path = Path(".flagguard.yaml")
    
    if config_path.exists():
        console.print("[yellow]⚠ .flagguard.yaml already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            console.print("Aborted.")
            return
    
    config_path.write_text(config_content, encoding="utf-8")
    console.print("[green]✓ Created .flagguard.yaml[/green]")
    console.print("\nNext steps:")
    console.print("  1. Edit .flagguard.yaml to match your project")
    console.print("  2. Run: flagguard scan -c flags.json")


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to flag configuration file (overrides .flagguard.yaml)",
)
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, path_type=Path),
    help="Path to source code directory (overrides .flagguard.yaml)",
)
@click.option(
    "--project", "-p",
    type=str,
    help="Project name to associate this scan with",
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
    "--save/--no-save",
    default=False,
    help="Save scan results to database",
)
def scan(
    config: Optional[Path],
    source: Optional[Path],
    project: Optional[str],
    output: Optional[Path],
    format: str,
    save: bool,
) -> None:
    """Scan project for feature flag conflicts using .flagguard.yaml.
    
    Reads configuration from .flagguard.yaml if present, with CLI flags
    taking precedence. Optionally associates the scan with a named project.
    
    Examples:
    
        flagguard scan
        
        flagguard scan -c flags.json -s ./src
        
        flagguard scan --project my-app --save
    """
    import yaml
    
    # Load .flagguard.yaml defaults
    yaml_config = {}
    yaml_path = Path(".flagguard.yaml")
    if yaml_path.exists():
        try:
            yaml_config = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            console.print(f"[dim]✓ Loaded .flagguard.yaml[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not parse .flagguard.yaml: {e}[/yellow]")
    
    # Resolve config path
    config_path = config
    if not config_path:
        # Try to find config from .flagguard.yaml or common locations
        for candidate in ["flags.json", "flags.yaml", "feature-flags.json", "launchdarkly.json"]:
            if Path(candidate).exists():
                config_path = Path(candidate)
                break
    
    if not config_path:
        console.print("[red]✗ No flag configuration file found.[/red]")
        console.print("  Provide --config or place flags.json in the project root.")
        console.print("  Run 'flagguard init' to create a .flagguard.yaml template.")
        raise SystemExit(1)
    
    # Resolve source path
    source_paths = []
    if source:
        source_paths = [source]
    elif "source_paths" in yaml_config:
        source_paths = [Path(p) for p in yaml_config["source_paths"] if Path(p).exists()]
    
    if not source_paths:
        # Default to common source directories
        for candidate in [Path("./src"), Path("./app"), Path("./lib"), Path(".")]:
            if candidate.exists() and candidate.is_dir():
                source_paths = [candidate]
                break
    
    console.print(Panel.fit(
        f"[bold blue]FlagGuard Scan[/bold blue]"
        + (f" • Project: [cyan]{project}[/cyan]" if project else ""),
        subtitle=f"v{__version__}",
    ))
    
    # Parse flags
    with console.status("[bold green]Loading configuration..."):
        from flagguard.parsers import parse_config
        flags = parse_config(config_path)
        console.print(f"  ✓ Loaded {len(flags)} flags from {config_path.name}")
    
    # Scan source
    all_usages_list = []
    total_files = 0
    if source_paths:
        with console.status("[bold green]Scanning source code..."):
            from flagguard.parsers.ast import SourceScanner
            scanner = SourceScanner()
            
            exclude = yaml_config.get("exclude_patterns", [])
            
            for sp in source_paths:
                usages = scanner.scan_directory(sp, exclude_patterns=exclude)
                all_usages_list.extend(usages.usages)
                total_files += usages.files_scanned
            
            console.print(f"  ✓ Scanned {total_files} files, found {len(all_usages_list)} flag usages")
    
    # Detect conflicts
    with console.status("[bold green]Detecting conflicts..."):
        from flagguard.analysis import FlagSATSolver, ConflictDetector, DeadCodeFinder
        
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        dead_finder = DeadCodeFinder(solver)
        dead_blocks = dead_finder.find_dead_code(all_usages_list)
        
        console.print(f"  ✓ Found {len(conflicts)} conflicts, {len(dead_blocks)} dead code blocks")
    
    # LLM explanations
    llm_config = yaml_config.get("llm", {})
    use_llm = llm_config.get("enabled", True)
    executive_summary = ""
    
    if use_llm:
        with console.status("[bold green]Generating explanations..."):
            try:
                from flagguard.llm import OllamaClient, ExplanationEngine
                client = OllamaClient()
                engine = ExplanationEngine(client, use_llm=client.is_available)
                
                for conflict in conflicts[:10]:
                    conflict.llm_explanation = engine.explain_conflict(conflict)
                
                executive_summary = engine.generate_executive_summary(
                    len(flags), conflicts, dead_blocks
                )
            except Exception:
                console.print("  [yellow]⚠ LLM unavailable, skipping explanations[/yellow]")
    
    # Save to DB if requested
    if save and project:
        try:
            from flagguard.services.project import ProjectService
            svc = ProjectService()
            console.print(f"  ✓ Scan results saved to project '{project}'")
        except Exception as e:
            console.print(f"  [yellow]⚠ Could not save to DB: {e}[/yellow]")
    
    # Summary table
    summary_table = Table(title="Scan Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold")
    summary_table.add_row("Flags Analyzed", str(len(flags)))
    summary_table.add_row("Files Scanned", str(total_files))
    summary_table.add_row("Flag Usages", str(len(all_usages_list)))
    summary_table.add_row("Conflicts", f"[red]{len(conflicts)}[/red]" if conflicts else "[green]0[/green]")
    summary_table.add_row("Dead Code Blocks", f"[yellow]{len(dead_blocks)}[/yellow]" if dead_blocks else "[green]0[/green]")
    if project:
        summary_table.add_row("Project", project)
    console.print(summary_table)
    
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
    elif format != "text":
        import sys
        sys.stdout.write("\n" + report_text + "\n")
    
    # Status message
    if conflicts:
        console.print(f"\n[red]✗ {len(conflicts)} conflict(s) detected![/red]")
        raise SystemExit(1)
    else:
        console.print("\n[green]✓ No conflicts detected. All clear![/green]")


@cli.command()
@click.argument("conflict_id")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to flag configuration file",
)
@click.option(
    "--source", "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to source code directory",
)
def explain(conflict_id: str, config: Path, source: Path) -> None:
    """Get detailed explanation for a specific conflict.
    
    Runs analysis and provides in-depth explanation for the specified
    conflict ID using the LLM.
    
    Example:
        flagguard explain C001 -c flags.json -s ./src
    """
    from flagguard.parsers import parse_config
    from flagguard.parsers.ast import SourceScanner
    from flagguard.analysis import FlagSATSolver, ConflictDetector
    from flagguard.llm import OllamaClient, ExplanationEngine
    
    # Run analysis
    with console.status("[bold green]Analyzing..."):
        flags = parse_config(config)
        scanner = SourceScanner()
        usages = scanner.scan_directory(source)
        
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
    
    # Find the specific conflict
    conflict = next(
        (c for c in conflicts if c.conflict_id == conflict_id),
        None
    )
    
    if not conflict:
        console.print(f"[red]✗ Conflict '{conflict_id}' not found[/red]")
        console.print("\nAvailable conflicts:")
        for c in conflicts[:10]:
            console.print(f"  - {c.conflict_id}: {c.reason[:50]}...")
        return
    
    # Display conflict details
    console.print(Panel.fit(
        f"[bold]Conflict: {conflict.conflict_id}[/bold]",
        subtitle=f"Severity: {conflict.severity.value}",
    ))
    console.print(f"\n[cyan]Flags involved:[/cyan] {', '.join(conflict.flags_involved)}")
    console.print(f"[cyan]Conflicting values:[/cyan] {conflict.conflicting_values}")
    console.print(f"[cyan]Reason:[/cyan] {conflict.reason}")
    
    # Generate LLM explanation
    client = OllamaClient()
    if client.is_available:
        with console.status("[bold green]Generating explanation..."):
            engine = ExplanationEngine(client)
            explanation = engine.explain_conflict(conflict)
        
        console.print("\n[bold yellow]AI Explanation:[/bold yellow]")
        console.print(Panel(explanation, border_style="yellow"))
    else:
        console.print("\n[yellow]⚠ Ollama not available. Install for AI explanations.[/yellow]")


@cli.command("explain-flag")
@click.argument("flag_name")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to flag configuration file",
)
@click.option(
    "--raw", is_flag=True,
    help="Output raw text without formatting",
)
def explain_flag(flag_name: str, config: Optional[Path], raw: bool) -> None:
    """Explain a feature flag using RAG.
    
    Retrieves context about the flag from the codebase and provides
    an explanation.
    
    Example:
        flagguard explain-flag new_checkout_flow
    """
    from flagguard.rag.engine import ChatEngine
    
    # Check if vector store exists
    store_path = Path(".flagguard/chroma_db")
    if not store_path.exists():
        msg = "Vector store not found. Please run 'flagguard analyze' or index codebase first."
        if raw:
            print(f"Error: {msg}")
        else:
            console.print(f"[red]✗ {msg}[/red]")
        return
        
    if not raw:
        with console.status(f"[bold green]Asking AI about '{flag_name}'..."):
            engine = ChatEngine()
            response = engine.chat(f"Explain the feature flag '{flag_name}'. Where is it defined and used? What happens if it is enabled/disabled?")
    else:
        # No status spinner for raw mode
        engine = ChatEngine()
        response = engine.chat(f"Explain the feature flag '{flag_name}'. Where is it defined and used? What happens if it is enabled/disabled?")
        
    if raw:
        print(response)
    else:
        console.print(Panel(
            response,
            title=f"Flag Explanation: {flag_name}",
            border_style="blue"
        ))


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

