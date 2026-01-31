# FlagGuard User Guide

This guide covers how to use FlagGuard to analyze your feature flag configurations and codebases.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration Formats](#configuration-formats)
4. [CLI Commands](#cli-commands)
5. [Understanding Output](#understanding-output)
6. [CI/CD Integration](#cicd-integration)
7. [Web Interface](#web-interface)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Using pip

```bash
pip install flagguard
```

### Using uv (recommended)

```bash
uv pip install flagguard
```

### From source

```bash
git clone https://github.com/yourusername/flagguard.git
cd flagguard
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Prepare your configuration

FlagGuard supports multiple configuration formats. Create or export your flag configuration:

```json
{
  "flags": [
    {"name": "feature_a", "enabled": true},
    {"name": "feature_b", "enabled": true, "dependencies": ["feature_a"]}
  ]
}
```

### 2. Run analysis

```bash
flagguard analyze --config flags.json --source ./src
```

### 3. Review results

FlagGuard will report:
- ✅ Number of flags analyzed
- ⚠️ Conflicts detected
- 🔍 Dead code blocks found

---

## Configuration Formats

### LaunchDarkly JSON

Export from LaunchDarkly dashboard or use the API:

```json
{
  "flags": {
    "my_flag": {
      "key": "my_flag",
      "on": true,
      "prerequisites": [{"key": "required_flag"}]
    }
  }
}
```

### Unleash YAML

```yaml
features:
  - name: my_flag
    enabled: true
    strategies:
      - name: default
```

### Generic JSON

```json
{
  "flags": [
    {
      "name": "my_flag",
      "enabled": true,
      "dependencies": ["required_flag"]
    }
  ]
}
```

---

## CLI Commands

### analyze

Full analysis with conflict detection and dead code finding:

```bash
# Basic usage
flagguard analyze --config flags.json --source ./src

# With output file
flagguard analyze -c flags.json -s ./src -o report.md -f markdown

# Without LLM explanations
flagguard analyze -c flags.json -s ./src --no-llm
```

### parse

Validate and display flag configuration:

```bash
flagguard parse --config flags.json
```

### graph

Generate dependency graph:

```bash
flagguard graph --config flags.json -o deps.mermaid
```

### check-llm

Verify Ollama availability:

```bash
flagguard check-llm
```

---

## Understanding Output

### Conflict Report

```
[CRITICAL] C001: new_checkout, payment_gateway
  Conflicting State: new_checkout=True, payment_gateway=False
  Reason: Flag 'new_checkout' requires 'payment_gateway', which is disabled
```

**Severity Levels:**
- 🔴 **CRITICAL**: Production will break
- 🟠 **HIGH**: Significant issue
- 🟡 **MEDIUM**: Should be addressed
- 🟢 **LOW**: Minor concern

### Dead Code Report

```
DEAD CODE: src/billing.py:45-67 (22 lines)
  Requires: premium_tier=True, payment_gateway=True
  Reason: payment_gateway is always disabled
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Feature Flag Analysis

on: [pull_request]

jobs:
  flagguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Analyze Flags
        uses: ./
        with:
          config-path: './flags.json'
          source-path: './src'
          fail-on-conflict: 'true'
```

### GitLab CI

```yaml
flagguard:
  image: python:3.11
  script:
    - pip install flagguard
    - flagguard analyze --config flags.json --source ./src --format json -o report.json
  artifacts:
    paths:
      - report.json
```

---

## Web Interface

Launch the Gradio web interface:

```bash
python -m flagguard.ui.app
```

Access at `http://localhost:7860`

Features:
- Upload configuration files
- View analysis results
- Generate dependency graphs
- AI-powered explanations

---

## Troubleshooting

### "No flags found in configuration"

- Ensure your configuration format matches one of the supported formats
- Check for JSON/YAML syntax errors
- Verify the file path is correct

### "SAT solver not available"

Z3 is required for conflict detection:

```bash
pip install z3-solver
```

### "LLM unavailable"

For AI explanations, install and run Ollama:

1. Install from https://ollama.ai
2. Pull the model: `ollama pull gemma2:2b`
3. Verify: `flagguard check-llm`

### Parser errors

- LaunchDarkly: Must have `flags` key with nested objects
- Unleash: Must have `features` key with array
- Generic: Array of flag objects or `flags` key

---

## Getting Help

- [GitHub Issues](https://github.com/yourusername/flagguard/issues)
- [Documentation](https://flagguard.readthedocs.io)
- [Examples](../examples/)

---

*Last updated: January 2026*
