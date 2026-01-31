# FlagGuard 🚩

**AI-Powered Feature Flag Conflict Analyzer**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FlagGuard is a static analysis tool that detects conflicts, impossible states, and dead code in feature flag configurations. It combines AST parsing, SAT solving, and LLM explanations to help you maintain healthy feature flag systems.

## 🎯 Key Features

- **Conflict Detection**: Uses Z3 SAT solver to find impossible flag combinations
- **Dead Code Finder**: Identifies code that can never execute due to flag configurations
- **Dependency Graph**: Visualizes flag relationships with Mermaid diagrams
- **Multi-Platform Support**: Parses LaunchDarkly, Unleash, and generic JSON configs
- **LLM Explanations**: Uses Ollama with Gemma 2B for human-readable explanations
- **CLI & Web UI**: Command-line interface and Gradio-based web interface

## 🚀 Quick Start

### Installation

```bash
# Using pip
pip install flagguard

# Using uv (recommended)
uv pip install flagguard
```

### Basic Usage

```bash
# Analyze flags and source code
flagguard analyze --config flags.json --source ./src

# Parse and display configuration
flagguard parse --config flags.json

# Generate dependency graph
flagguard graph --config flags.json

# Check LLM availability
flagguard check-llm
```

### Web Interface

```bash
# Launch Gradio web UI
python -m flagguard.ui.app
```

## 📋 Configuration Formats

### LaunchDarkly JSON

```json
{
  "flags": {
    "new_checkout": {
      "key": "new_checkout",
      "on": true,
      "prerequisites": [{"key": "payment_enabled"}]
    }
  }
}
```

### Generic JSON

```json
{
  "flags": [
    {"name": "feature_a", "enabled": true},
    {"name": "feature_b", "enabled": true, "dependencies": ["feature_a"]}
  ]
}
```

### Unleash YAML

```yaml
features:
  - name: new_checkout
    enabled: true
    strategies:
      - name: default
```

## 🔧 Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/flagguard.git
cd flagguard

# Install with dev dependencies
uv pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/flagguard --cov-report=html

# Run specific test file
pytest tests/unit/test_parsers.py
```

### Code Quality

```bash
# Linting
ruff check src tests

# Type checking
mypy src

# Formatting
ruff format src tests
```

## 📊 Output Formats

### Markdown Report

```bash
flagguard analyze --config flags.json --source ./src --format markdown -o report.md
```

### JSON (for CI/CD)

```bash
flagguard analyze --config flags.json --source ./src --format json -o report.json
```

## 🤖 LLM Integration

FlagGuard uses Ollama for local LLM inference. Install Ollama and pull the default model:

```bash
# Install Ollama from https://ollama.ai
ollama pull gemma2:2b
```

Disable LLM features with `--no-llm` flag:

```bash
flagguard analyze --config flags.json --source ./src --no-llm
```

## 🏗️ Architecture

```
flagguard/
├── core/          # Data models and utilities
├── parsers/       # Config and source code parsers
│   └── ast/       # Tree-sitter based extractors
├── analysis/      # SAT solver and conflict detection
├── llm/           # Ollama integration
├── reporters/     # Output formatters
├── cli/           # Command-line interface
└── ui/            # Gradio web interface
```

## 📖 Documentation

- [Full Documentation](https://flagguard.readthedocs.io)
- [API Reference](https://flagguard.readthedocs.io/api)
- [Examples](./examples)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Z3 Theorem Prover](https://github.com/Z3Prover/z3) for SAT solving
- [Tree-sitter](https://tree-sitter.github.io) for AST parsing
- [Ollama](https://ollama.ai) for local LLM inference
- [Gradio](https://gradio.app) for the web interface

---

Made with ❤️ by the FlagGuard team
