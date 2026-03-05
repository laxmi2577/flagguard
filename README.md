# FlagGuard

<div align="center">
  <h3>Enterprise Feature Flag Intelligence Platform</h3>
  <p>FlagGuard detects <b>conflicts</b>, <b>impossible states</b>, and <b>dead code</b> using SAT solving, static analysis, and AI-powered explanations.</p>
  
  [![PyPI](https://img.shields.io/pypi/v/flagguard)](https://pypi.org/project/flagguard/)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
  [![Tests](https://github.com/laxmi2577/flagguard/actions/workflows/test.yml/badge.svg)](https://github.com/laxmi2577/flagguard/actions)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
</div>

---

## 🚨 The Problem: Feature Flag Debt

Companies with over 100 feature flags often suffer from "flag debt." 
Flags interact in unexpected ways—enabling Flag A while Flag B is turned off may crash the app. Furthermore, dead code behind permanently disabled flags bloats the codebase and causes confusion during onboarding and deployment.

**FlagGuard** solves this by shifting feature flag analysis left. It mathematically proves impossible states *before* you deploy.

---

## 🌟 Key Features

- **SAT-Based Conflict Detection:** Finds impossible flag combinations securely offline using Microsoft's Z3 solver.
- **Dead Code Finder:** Identifies unreachable code blocks directly inside Python and JavaScript/TypeScript Source Code.
- **Multi-Platform Parsers:** Ingests LaunchDarkly JSON, Unleash YAML, or Custom JSON configurations.
- **AI-Powered Insights:** Uses Local LLMs (Ollama + Gemma 2b) to generate plain-English explanations for complex mathematical conflicts.
- **Interactive Dashboards:** Built-in Gradio Liquid Glass Web UI and FastAPI REST backend for team collaboration.
- **CI/CD Native:** Includes a sleek Command-Line Interface (CLI) and GitHub Action for automated pull request gating.

---

## 📚 Documentation Directory

We've modularized our documentation for easy navigation. Click to explore:

- 🚀 [**Installation & User Guide**](docs/INSTALLATION.md) — How to install via `pip`/`uv`, set up CI/CD, and run the UI.
- 🏗️ [**Architecture & System Design**](docs/ARCHITECTURE.md) — Component teardown, SAT solver explanation, and database models.
- 🔌 [**API Reference & SDK**](docs/API_DOCUMENTATION.md) — Documentation for the Python SDK, REST API endpoints, and CLI commands.
- 🤝 [**Contributing Guidelines**](docs/CONTRIBUTING.md) — How to submit PRs, run local tests, and add new parsers.

---

## 🛠️ Quick Start

Install FlagGuard using [`uv`](https://github.com/astral-sh/uv) or `pip`:

```bash
uv tool install flagguard
```

Analyze your codebase directly from the terminal:

```bash
flagguard analyze --config flags.json --source ./src
```

Or spin up the **interactive Web UI Dashboard**:

```bash
uv run python src/flagguard/ui/app.py
```
*Login with `admin@example.com` / `Admin@123` at http://localhost:7860.*

---

## 🗺️ Roadmap & Future Improvements

**Upcoming Highlights (v0.2.0 - v1.0.0):**
- **Language Expansion:** Go, Java, and Ruby AST parsing support.
- **Enterprise Integrations:** Split.io, ConfigCat integrations, and SAML SSO.
- **Performance Improvements:** Incremental PR analysis and AST syntax tree caching.
- **Developer Experience:** VS Code extension and SARIF output formats for advanced security scanning.

Have an idea? Please open a [Feature Request](https://github.com/laxmi2577/flagguard/issues/new) on GitHub!

---

## 📄 License & Community

FlagGuard is **MIT Licensed** — see [LICENSE](LICENSE) for details.

- Need help? Read our [Support Guidelines](SUPPORT.md).
- Have a security concern? Read our [Security Policy](SECURITY.md).
- Want to contribute? Check out the [Contributing Guidelines](docs/CONTRIBUTING.md).

<div align="center">
  <i>Built with care for the feature flag engineering community.</i>
</div>
