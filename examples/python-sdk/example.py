"""Example: Basic FlagGuard usage with Python API."""

from pathlib import Path

from flagguard import FlagGuardAnalyzer


def main() -> None:
    """Demonstrate basic FlagGuard usage."""
    
    # Initialize analyzer
    analyzer = FlagGuardAnalyzer(
        explain_with_llm=False,  # Set to True if Ollama is available
    )
    
    # Run analysis
    config_path = Path("flags.json")
    source_path = Path("./src")
    
    if not config_path.exists():
        print("Please create a flags.json file first")
        return
    
    report = analyzer.analyze(
        config_path=config_path,
        source_path=source_path,
        output_format="markdown",
    )
    
    # Access results
    print(f"Flags analyzed: {report.get('flags_analyzed', 0)}")
    print(f"Conflicts found: {len(report.get('conflicts', []))}")
    
    # Print conflicts
    for conflict in report.get("conflicts", []):
        severity = conflict.get("severity", "unknown")
        flags = conflict.get("flags_involved", [])
        reason = conflict.get("reason", "")
        print(f"  [{severity.upper()}] {', '.join(flags)}: {reason}")


if __name__ == "__main__":
    main()
