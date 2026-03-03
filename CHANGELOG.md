# Changelog

All notable changes to FlagGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-03

### Added
- **REST API Gateway (FastAPI)**
  - 31 endpoints with auto-generated Swagger docs at `/docs`
  - Full CRUD for Projects, Scans, Flags, Environments, Webhooks
  - JWT OAuth2 authentication
  - Health check endpoints

- **Role-Based Access Control (RBAC)**
  - Three roles: admin, analyst, viewer
  - Role hierarchy enforcement on all API endpoints
  - Admin-only user management (list, update roles)

- **Multi-Environment Support**
  - Create dev, staging, prod environments per project
  - Flag override configurations per environment
  - Drift detection: compare flag states across environments

- **Webhook & Notification System**
  - Configure webhook URLs per project
  - Event-based notifications (scan.completed, conflict.detected, etc.)
  - HMAC-SHA256 signed payloads for security
  - Async dispatch via thread pool
  - Test endpoint for connectivity verification

- **Audit Trail**
  - Immutable audit log for compliance
  - Tracks user actions, resource changes, logins

- **CLI `scan` Command**
  - Project-based workflow with `.flagguard.yaml` defaults
  - `--project` and `--save` flags for DB persistence

- **Liquid Glass UI Redesign**
  - Royal Obsidian theme (dark background, gold/silver accents)
  - Frosted glass panels with shimmer borders
  - Floating orb login screen
  - Interactive Plotly charts with gold/emerald palette
  - Outfit + Inter typography

### Changed
- Database models expanded: Environment, WebhookConfig, AuditLog tables
- User model now includes `role` column for RBAC
- Scan model supports `environment_id` for multi-env scanning

## [1.0.0] - 2026-02-15

### Added
- **Web Dashboard (Gradio UI)**
  - Interactive dashboard with Plotly charts
  - Dependency graph with Mermaid rendering
  - Project management (create, switch projects)
  - File upload for configs and source archives
  - AI Chat with RAG-powered assistant
  - Login authentication

- **Database Layer**
  - SQLAlchemy ORM with SQLite/PostgreSQL support
  - User, Project, Scan, ScanResult models
  - JWT authentication for API routes

- **RAG Integration**
  - ChromaDB vector store for document indexing
  - AI chat engine for interactive flag analysis

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

[2.0.0]: https://github.com/laxmi2577/flagguard/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/laxmi2577/flagguard/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/laxmi2577/flagguard/releases/tag/v0.1.0
[0.0.1]: https://github.com/laxmi2577/flagguard/releases/tag/v0.0.1
