# FlagGuard Installation & User Guide

FlagGuard detects conflicts, impossible states, and dead code in your feature flag configurations using SAT solving and static analysis.

---

## 🚀 Installation

### Using pip
```bash
pip install flagguard
```

### Using uv (recommended)
```bash
uv tool install flagguard
```

### From source (for development)
```bash
git clone https://github.com/laxmi2577/flagguard.git
cd flagguard
uv sync
```

---

## 🛠️ Configuration Formats

FlagGuard supports multiple feature flag configuration formats:

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

## 🖥️ Local Usage

### 1. Web Dashboard (Recommended)
FlagGuard comes with a beautiful, interactive "Liquid Glass" web interface.
```bash
uv run python src/flagguard/ui/app.py
```
- Open `http://localhost:7860`
- Login: `admin@example.com` / `Admin@123`
- Use the **Analysis** tab to create projects and run scans visually.

### 2. REST API Server
```bash
uv run uvicorn flagguard.api.server:app --port 8000
```
- Interactive Swagger documentation available at `http://localhost:8000/docs`

### 3. CLI Analysis
Analyze your flags directly from the terminal:
```bash
flagguard analyze --config flags.json --source ./src
```

---

## 🤖 AI & LLM Integration (Ollama)

For AI-powered plain-English explanations of conflicts, you need [Ollama](https://ollama.ai) installed locally.

1. Install Ollama.
2. Pull the model: `ollama pull gemma2:2b`
3. Verify status: `flagguard check-llm`

---

## 🔄 CI/CD Integration

Gate your deployments by adding FlagGuard to your CI pipeline.

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
        uses: laxmi2577/flagguard@v1
        with:
          config-path: './flags.json'
          source-path: './src'
          fail-on-critical: 'true'
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

## 🔧 Troubleshooting

### "No flags found in configuration"
- Ensure your configuration format matches one of the supported formats.
- Check for JSON/YAML syntax errors.

### "SAT solver not available"
Z3 is required for conflict detection. If missing:
```bash
pip install z3-solver
```

### Analysis is slow with large codebases
- Use `--max-conflicts 50` to limit output
- Exclude test directories with patterns
- Run FlagGuard on changed files only
