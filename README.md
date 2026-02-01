# 🚩 FlagGuard

**AI Feature Flag Conflict Analyzer**

[![PyPI](https://img.shields.io/pypi/v/flagguard)](https://pypi.org/project/flagguard/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/yourusername/flagguard/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/flagguard/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

FlagGuard detects **conflicts**, **impossible states**, and **dead code** in your feature flag configurations using SAT solving and static analysis.

## 🎯 The Problem

- Companies with 100+ feature flags face "flag debt"
- Flags interact in unexpected ways—enabling Flag A while Flag B is off may crash the app
- Dead code behind never-enabled flags bloats the codebase
- **Knight Capital lost $440M** partly due to a feature flag misconfiguration

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Conflict Detection** | Find impossible flag combinations using SAT solving |
| **Dead Code Finder** | Identify unreachable code paths |
| **Dependency Graph** | Visualize flag relationships with Mermaid |
| **LLM Explanations** | Plain English conflict descriptions (via Ollama) |
| **CI Integration** | GitHub Action to block deploys with conflicts |
| **Multi-Platform** | Support for LaunchDarkly, Unleash, and custom formats |

## 📦 Installation

```bash
pip install flagguard
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add flagguard
```

## 🚀 Quick Start

```bash
# Analyze your flags
flagguard analyze --config flags.json --source ./src

# Just parse and display flags
flagguard parse --config flags.json

# Generate dependency graph
flagguard graph --config flags.json

# Check LLM availability
flagguard check-llm
```

### Example Output

```
╭────────────────────╮
│ FlagGuard Analysis │
╰────── v0.1.0 ──────╯
✓ Loaded 4 flags from flags.json
✓ Scanned 15 files, found 23 flag usages
✓ Found 3 conflicts, 1 dead code block

CONFLICTS:
  [CRITICAL] C001: Flags premium, payment cannot both be enabled
  [HIGH] C002: Enabling premium requires payment to be enabled
```

## 📖 Supported Formats

| Platform | Format | Status |
|----------|--------|--------|
| LaunchDarkly | JSON | ✅ Full support |
| Unleash | YAML/JSON | ✅ Full support |
| Custom | JSON | ✅ Full support |

## 🔧 GitHub Action

Add FlagGuard to your CI pipeline:

```yaml
name: Feature Flag Check
on: [pull_request]

jobs:
  flagguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run FlagGuard
        uses: yourusername/flagguard@v1
        with:
          config-path: 'flags/config.json'
          source-path: 'src'
          fail-on-critical: 'true'
```

## 🖥️ Web UI

Launch the Gradio web interface:

```bash
python -m flagguard.ui.app
```

Then open http://localhost:7860 in your browser.

## 📚 CLI Reference

| Command | Description |
|---------|-------------|
| `flagguard analyze` | Full analysis with conflict detection |
| `flagguard parse` | Parse and display flag configuration |
| `flagguard graph` | Generate Mermaid dependency diagram |
| `flagguard check-llm` | Verify Ollama/LLM availability |
| `flagguard init` | Create .flagguard.yaml config template |
| `flagguard explain` | Get detailed LLM explanation for a conflict |

## 🔌 Python API

```python
from flagguard import FlagGuardAnalyzer
from pathlib import Path

analyzer = FlagGuardAnalyzer(explain_with_llm=False)
report = analyzer.analyze(
    config_path=Path("flags.json"),
    source_path=Path("./src"),
    output_format="markdown",
)

print(f"Found {len(report['conflicts'])} conflicts")
```

## 🏗️ Architecture

```
flagguard/
├── parsers/          # Config & AST parsers
│   ├── launchdarkly.py
│   ├── unleash.py
│   └── ast/          # Python/JS source parsing
├── analysis/         # SAT solver & conflict detection
│   ├── z3_wrapper.py
│   ├── conflict_detector.py
│   └── dead_code.py
├── llm/              # LLM integration
│   ├── ollama_client.py
│   └── explainer.py
├── reporters/        # Output formatters
│   ├── markdown.py
│   └── json_reporter.py
├── cli/              # Command-line interface
└── ui/               # Gradio web interface
```

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

```bash
# Setup development environment
git clone https://github.com/yourusername/flagguard.git
cd flagguard
uv sync
uv run pytest tests/ -v
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with ❤️ for the feature flag community
