# API Reference

## Core Classes

### FlagGuardAnalyzer

Main entry point for programmatic usage.

```python
from flagguard import FlagGuardAnalyzer
from pathlib import Path

analyzer = FlagGuardAnalyzer(explain_with_llm=True)
report = analyzer.analyze(
    config_path=Path("flags.json"),
    source_path=Path("./src"),
    output_path=Path("report.md"),
    output_format="markdown",
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `explain_with_llm` | bool | True | Enable LLM-powered explanations |
| `output_format` | str | "markdown" | Output format (markdown, json) |

#### Methods

**`analyze(config_path, source_path, output_path=None, output_format="markdown")`**

Run full analysis pipeline.

- **config_path** (Path): Path to flag configuration file
- **source_path** (Path): Path to source code directory
- **output_path** (Path, optional): Save report to file
- **output_format** (str): Report format

Returns: `dict` with analysis results

---

## Data Models

### FlagDefinition

Represents a feature flag.

```python
from flagguard.core.models import FlagDefinition, FlagType

@dataclass
class FlagDefinition:
    name: str
    flag_type: FlagType
    enabled: bool
    default_variation: str = ""
    variations: list[FlagVariation] = field(default_factory=list)
    targeting_rules: list[TargetingRule] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
```

### Conflict

Represents a detected conflict.

```python
from flagguard.core.models import Conflict, ConflictSeverity

@dataclass
class Conflict:
    conflict_id: str
    flags_involved: list[str]
    conflicting_values: dict[str, bool]
    severity: ConflictSeverity
    reason: str
    llm_explanation: str = ""
```

### ConflictSeverity

```python
class ConflictSeverity(Enum):
    CRITICAL = "critical"  # Impossible state
    HIGH = "high"          # Dependency violation
    MEDIUM = "medium"      # Potential issue
    LOW = "low"            # Informational
```

---

## Parsers

### parse_config

Parse a configuration file.

```python
from flagguard.parsers import parse_config
from pathlib import Path

flags = parse_config(Path("flags.json"))
# Auto-detects format, or specify:
flags = parse_config(Path("flags.json"), format="launchdarkly")
```

### SourceScanner

Scan source code for flag usages.

```python
from flagguard.parsers.ast import SourceScanner
from pathlib import Path

scanner = SourceScanner()
result = scanner.scan_directory(Path("./src"))

print(f"Scanned {result.files_scanned} files")
print(f"Found {len(result.usages)} flag usages")
```

---

## Analysis

### FlagSATSolver

Z3-based SAT solver for flag constraints.

```python
from flagguard.analysis import FlagSATSolver

solver = FlagSATSolver()
solver.add_requires("child", "parent")
solver.add_conflicts_with("premium", "free")

# Check if a state is possible
possible = solver.check_state_possible({
    "child": True,
    "parent": True,
})
```

### ConflictDetector

Detect conflicts in flag configurations.

```python
from flagguard.analysis import FlagSATSolver, ConflictDetector

solver = FlagSATSolver()
detector = ConflictDetector(solver)
detector.load_flags(flags)

conflicts = detector.detect_all_conflicts()
```

---

## CLI Reference

### flagguard analyze

```
Usage: flagguard analyze [OPTIONS]

Options:
  -c, --config PATH     Flag configuration file [required]
  -s, --source PATH     Source code directory [required]
  -o, --output PATH     Output file path
  -f, --format TEXT     Output format (markdown, json, text)
  --use-llm/--no-llm    Enable/disable LLM explanations
```

### flagguard parse

```
Usage: flagguard parse [OPTIONS]

Options:
  -c, --config PATH     Flag configuration file [required]
```

### flagguard graph

```
Usage: flagguard graph [OPTIONS]

Options:
  -c, --config PATH     Flag configuration file [required]
  -o, --output PATH     Output file for Mermaid diagram
```

### flagguard init

```
Usage: flagguard init

Creates .flagguard.yaml configuration template.
```

### flagguard check-llm

```
Usage: flagguard check-llm

Checks Ollama availability and model status.
```

### flagguard explain

```
Usage: flagguard explain CONFLICT_ID [OPTIONS]

Options:
  -c, --config PATH     Flag configuration file [required]
  -s, --source PATH     Source code directory [required]
```
