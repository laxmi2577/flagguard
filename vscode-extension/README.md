# FlagGuard VS Code Extension

Real-time feature flag conflict detection directly in your editor.

![FlagGuard](https://img.shields.io/badge/FlagGuard-v0.1.0-blue)
![VS Code](https://img.shields.io/badge/VS%20Code-1.85+-green)

## Features

### 🔍 Real-time Analysis
Automatically analyze your feature flags when you save files.

### 📋 Problems Panel Integration
See conflicts and dead code directly in the Problems panel with severity color coding.

### 🚩 Hover Information
Hover over flag names in your code to see details.

### 📊 Status Bar
Quick status indicator showing analysis results.

### 🔗 Code Lens
Inline annotations above flag usages in your code.

## Requirements

- VS Code 1.85+
- Python 3.10+ with FlagGuard installed:
  ```bash
  pip install flagguard
  # or
  uv add flagguard
  ```

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `flagguard.enabled` | `true` | Enable/disable FlagGuard analysis |
| `flagguard.configPath` | `""` | Path to flag config (auto-detected) |
| `flagguard.analyzeOnSave` | `true` | Run analysis on file save |
| `flagguard.pythonPath` | `"python"` | Python executable path |
| `flagguard.showStatusBar` | `true` | Show status bar item |

## Commands

- `FlagGuard: Analyze Workspace` - Run analysis manually
- `FlagGuard: View Report` - Open analysis report
- `FlagGuard: Configure` - Open settings
- `FlagGuard: Clear Diagnostics` - Clear all warnings

## Usage

1. Open a project with a `flags.json` or `.flagguard.yaml` file
2. The extension automatically activates
3. Save any Python/JavaScript file to trigger analysis
4. View results in the Problems panel

## Building from Source

```bash
cd vscode-extension
npm install
npm run compile
```

To package as `.vsix`:
```bash
npm run package
```

## License

MIT License - see [LICENSE](../LICENSE)

---

Made with ❤️ by [Laxmi Ranjan](https://github.com/laxmi2577)
