---
title: FlagGuard
emoji: ðŸš©
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
license: mit
---

# FlagGuard - AI Feature Flag Conflict Analyzer

Detect conflicts, impossible states, and dead code in your feature flags.

## Features

- Parse LaunchDarkly, Unleash, and custom JSON/YAML configs
- Scan Python and JavaScript source code
- Detect impossible flag combinations using SAT solving
- Find dead code behind never-enabled flags
- Generate dependency graphs

## Usage

1. Upload your feature flag configuration (JSON/YAML)
2. Optionally upload your source code as a ZIP
3. Click Analyze
4. Review the report

## Local Installation

```bash
pip install flagguard
flagguard analyze --config flags.json --source ./src
```

## Links

- [GitHub Repository](https://github.com/laxmi2577/flagguard)
- [PyPI Package](https://pypi.org/project/flagguard/)
