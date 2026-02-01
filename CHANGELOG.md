# Changelog

All notable changes to FlagGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future features will be listed here

## [0.1.0] - 2026-02-01

### Added
- **Core Analysis**
  - SAT-based conflict detection using Z3 solver
  - Dead code detection for unreachable flag conditions
  - Dependency graph generation (Mermaid format)
  
- **Parsers**
  - LaunchDarkly JSON configuration parser
  - Unleash YAML/JSON configuration parser
  - Generic JSON format support
  - Python source code scanner (tree-sitter)
  - JavaScript source code scanner (tree-sitter)

- **LLM Integration**
  - Ollama client for local LLM support
  - Conflict explanation generation
  - Executive summary generation
  - Dead code explanation

- **CLI**
  - `flagguard analyze` - Full analysis pipeline
  - `flagguard parse` - Parse and display flags
  - `flagguard graph` - Generate dependency graph
  - `flagguard check-llm` - Verify Ollama availability
  - `flagguard init` - Create configuration template
  - `flagguard explain` - Explain specific conflict

- **Web UI**
  - Gradio-based web interface
  - File upload for configs and source code
  - Interactive analysis with report generation

- **CI/CD**
  - GitHub Action for CI integration
  - Release workflow for PyPI publishing
  - Security scanning workflow

- **Documentation**
  - Comprehensive README
  - API documentation
  - Contributing guide
  - Security policy

### Security
- Safe YAML loading (no code execution)
- Path traversal protection in source scanner
- Input validation for all parsers

## [0.0.1] - 2026-01-15

### Added
- Initial project structure
- Basic data models

---

[Unreleased]: https://github.com/laxmi2577/flagguard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/laxmi2577/flagguard/releases/tag/v0.1.0
[0.0.1]: https://github.com/laxmi2577/flagguard/releases/tag/v0.0.1
