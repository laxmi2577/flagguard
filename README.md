<div align="center">

# 🛡️ FlagGuard
**Enterprise-Grade AI Feature Flag Intelligence Platform**

<p align="center">
  <em>Mathematically proving feature flag safety before you deploy. Used to detect conflicts, dead code, and impossible states.</em>
</p>

[![PyPI](https://img.shields.io/pypi/v/flagguard?color=blue&style=for-the-badge)](https://pypi.org/project/flagguard/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen?style=for-the-badge)](https://github.com/laxmi2577/flagguard/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)

---

![FlagGuard Architecture](https://raw.githubusercontent.com/laxmi2577/flagguard/master/docs/assets/banner.png) *(Illustration placeholder)*

</div>

---

## 🚨 The Challenge: Technical Debt at Scale

In modern CI/CD pipelines, feature flags are essential. However, as organizations scale to **100+ active feature flags**, they introduce a dangerous new vector of technical debt:

*   **Silent Failures:** Enabling *Flag A* while *Flag B* is turned off can create unanticipated, untested execution paths that crash production. (The infamous 2012 Knight Capital $440M loss was fundamentally a feature flag collision).
*   **The "Dead Code" Swamp:** Engineering teams frequently leave code blocks protected by permanently disabled flags in the codebase for years, confusing new developers and bloating bundles.
*   **Undocumented Dependencies:** "Tribal knowledge" dictates that *Feature X* only works if *Service Y* is enabled, but this is never enforced in the code itself.

**FlagGuard** solves this by shifting feature flag analysis entirely to the **left**. Instead of waiting for runtime metrics to show failure, FlagGuard mathematically proves impossible states during the PR process.

---

## ⚡ Why Top Engineering Teams Need FlagGuard

Unlike standard linters, FlagGuard operates at the intersection of **Abstract Syntax Trees (AST)** and **Formal Verification**.

### 1. 🧠 SAT-Based Conflict Detection (Zero False Positives)
FlagGuard parses your codebase, translates your feature flag rules into Boolean logic equations, and feeds them into Mircosoft's **Z3 SMT Solver**. It mathematically calculates if two nested flag conditions represent an impossible state, guaranteeing zero false positives.

### 2. 🗑️ Automated Dead Code Elimination
By applying constraint solving against your codebase AST (via `tree-sitter`), FlagGuard flags code blocks that are mathematically unreachable based on your current LaunchDarkly, Unleash, or custom JSON/YAML flag configurations.

### 3. 🤖 Local AI Explanations via LLMs
Constraint solvers output complex algebraic failures. FlagGuard integrates with local **Ollama** instances (running models like Gemma 2b) to translate complex Boolean conflicts into plain-English, executive-friendly summaries directly in your PR comments.

### 4. 📊 Enterprise Dashboard & RBAC REST API
FlagGuard isn't just a CLI. It includes a beautiful, interactive "Liquid Glass" web UI built on Gradio, backed by a production-ready **FastAPI** backend featuring JWT Authentication, Role-Based Access Control, and SQLite/PostgreSQL persistence.

---

## 📚 Comprehensive Documentation Directory

We maintain rigorous documentation standards. Explore the architecture and usage guides below:

*   🚀 **[Installation & Quick Start Guide](docs/INSTALLATION.md)** — CLI installation, CI/CD pipeline integration, and Web UI setup.
*   🏗️ **[Architecture & System Design](docs/ARCHITECTURE.md)** — Deep dive into the Z3 SAT solver implementation, AST parsing, and relational database schema.
*   🔌 **[API Reference & SDK Docs](docs/API_DOCUMENTATION.md)** — Documentation for the Python SDK, 31 FastAPI REST endpoints, and CLI commands.
*   🤝 **[Contributing Guidelines](docs/CONTRIBUTING.md)** — How to submit PRs, run local tests, and add support for new parsers like Split.io.

---

## 🛠️ Quick Start Implementation

Install FlagGuard using [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`:

```bash
uv tool install flagguard
```

### 1. Perform a Static Codebase Audit
Execute a local mathematical proof of your feature flags against your source code:

```bash
flagguard analyze --config config/prod_flags.json --source ./src/backend --fail-on-critical
```

### 2. Launch the Enterprise Dashboard
Spin up the interactive Web UI and FastAPI backend to manage environments and view interactive dependency graphs:

```bash
# Start the web interface
uv run python src/flagguard/ui/app.py
```
*Login with `admin@example.com` / `Admin@123` at http://localhost:7860.*

---

## 🗺️ Engineering Roadmap (v0.2.0 - v1.0.0)

FlagGuard is actively developed with a focus on enterprise scalability:

- **[In Progress] Global Language Expansion:** High-performance AST parsing for Go, Java, and Ruby codebases.
- **[Planned] Enterprise Identiy:** SAML SSO integration and advanced Audit Logging retention.
- **[Planned] Developer Experience:** Official VS Code Extension for real-time mathematical conflict highlighting in IDE.
- **[Planned] Security Integrations:** SARIF output formats for direct ingestion into GitHub Advanced Security.

If you are a platform engineer with a feature request, please open a [GitHub Issue](https://github.com/laxmi2577/flagguard/issues/new).

---

## 👨‍💻 About the Author

**Laxmiranjan Sahu**  
*AI\ML Engineer*

FlagGuard was architected and developed from the ground up to address critical gaps in continuous delivery safety. I specialize in building highly resilient automation architectures, distributed systems, and QA infrastructure for enterprise applications.

Let's connect:
- 📧 **Email:** [laxmiranjan444@gmail.com](mailto:laxmiranjan444@gmail.com)
- 💼 **LinkedIn:** [linkedin.com/in/laxmiranjan](https://www.linkedin.com/in/laxmiranjan)
- 🌐 **Portfolio:** [laxmiranjansahu.vercel.app](https://laxmiranjansahu.vercel.app)
- 🐙 **GitHub:** [github.com/laxmi2577](https://github.com/laxmi2577)

---

## 🛡️ License & Project Governance

FlagGuard is Open Source and released under the **MIT License** — see the [LICENSE](LICENSE) file for details.

*   Need architectural support? Read our [Support Guidelines](SUPPORT.md).
*   Have a zero-day vulnerability to report? Read our secure [Security Policy](SECURITY.md).

<div align="center">
  <i>Architected with precision for the feature flag engineering community.</i>
</div>
