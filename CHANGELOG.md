# Changelog

All notable changes to FlagGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-03-11

### Added — AI Intelligence Layer (GraphRAG + Agentic Remediation)

- **AST-Aware Code Chunking** (`rag/ingester.py`)
  - Replaced naive 50-line sliding window with tree-sitter AST function-level extraction
  - Each chunk stores `function_name`, `class_name`, `start_line`, `end_line`, `flags_referenced`
  - Supports Python and JavaScript/TypeScript with regex fallback

- **Knowledge Graph** (`ai/graph.py`)
  - NetworkX-based directed call graph (which functions call which)
  - Transitive impact analysis via reverse BFS: given a flag conflict, find ALL affected functions
  - graph stats API for debugging and UI display

- **Hybrid Retriever** (`rag/retriever.py`)
  - Combines ChromaDB semantic search + NetworkX graph traversal
  - Intelligent merge, deduplication, and relevance-boosted ranking
  - Items found by both strategies ranked highest
  - Backwards-compatible `CheckRetriever` alias preserved

- **Agentic Remediation Loop** (`ai/agent.py`)
  - `CoderAgent`: Generates `git diff` patches using RAG-retrieved source context
  - `VerifierAgent`: Feeds patches through Z3 SAT solver for formal verification
  - `RemediationAgent`: Orchestrates Coder → Verifier → Retry (max 3 attempts)
  - Full reasoning chain tracking for UI display

- **RAG-Augmented Explainer** (`llm/explainer.py`, `llm/prompts.py`)
  - New `explain_conflict_with_fix()` method injects GraphRAG context into LLM prompts
  - New `RAG_CONFLICT_REMEDIATION_PROMPT` template for code-fix generation

- **AI Remediation Web UI Tab** (`ui/tabs/remediation.py`)
  - 🤖 AI Remediation tab with 3 sub-panels: Suggested Fix, Agent Reasoning, RAG Context
  - Interactive conflict selector and one-click fix generation

- **Test Suites**
  - `test_ast_chunker.py`: 10 tests covering AST chunking, flag extraction, metadata
  - `test_knowledge_graph.py`: 11 tests covering call graph, transitive callers, impact analysis

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

[3.0.0]: https://github.com/laxmi2577/flagguard/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/laxmi2577/flagguard/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/laxmi2577/flagguard/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/laxmi2577/flagguard/releases/tag/v0.1.0
[0.0.1]: https://github.com/laxmi2577/flagguard/releases/tag/v0.0.1
