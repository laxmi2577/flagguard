# Python SDK Example

This example demonstrates using FlagGuard as a Python library.

## Installation

```bash
pip install flagguard
```

## Usage

```python
from pathlib import Path
from flagguard import FlagGuardAnalyzer

# Initialize
analyzer = FlagGuardAnalyzer(explain_with_llm=False)

# Run analysis
report = analyzer.analyze(
    config_path=Path("flags.json"),
    source_path=Path("./src"),
)

# Access results
print(f"Conflicts: {len(report['conflicts'])}")

for conflict in report["conflicts"]:
    print(f"  [{conflict['severity']}] {conflict['reason']}")
```

## Available APIs

### FlagGuardAnalyzer

Main entry point for analysis.

```python
analyzer = FlagGuardAnalyzer(
    explain_with_llm=True,     # Use Ollama for explanations
    output_format="markdown",  # markdown or json
)
```

### parse_config

Parse flag configurations directly.

```python
from flagguard.parsers import parse_config

flags = parse_config(Path("flags.json"))
for flag in flags:
    print(f"{flag.name}: {'enabled' if flag.enabled else 'disabled'}")
```

### SourceScanner

Scan source code for flag usages.

```python
from flagguard.parsers.ast import SourceScanner

scanner = SourceScanner()
result = scanner.scan_directory(Path("./src"))
print(f"Found {len(result.usages)} flag usages")
```

### FlagSATSolver

Use the SAT solver directly.

```python
from flagguard.analysis import FlagSATSolver

solver = FlagSATSolver()
solver.add_requires("premium", "payment")

# Check if a state is possible
is_valid = solver.check_state_possible({
    "premium": True,
    "payment": True,
})  # True
```
