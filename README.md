# FlagGuard

**Enterprise Feature Flag Intelligence Platform**

[![PyPI](https://img.shields.io/pypi/v/flagguard)](https://pypi.org/project/flagguard/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/laxmi2577/flagguard/actions/workflows/test.yml/badge.svg)](https://github.com/laxmi2577/flagguard/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

FlagGuard detects **conflicts**, **impossible states**, and **dead code** in your feature flag configurations using SAT solving, static analysis, and AI-powered explanations.

---

## The Problem

- Companies with 100+ feature flags face "flag debt"
- Flags interact in unexpected ways -- enabling Flag A while Flag B is off may crash the app
- Dead code behind never-enabled flags bloats the codebase
- **Knight Capital lost $440M** partly due to a feature flag misconfiguration

---

## Features

### Core Analysis Engine
| Feature | Description |
|---------|-------------|
| **SAT-based Conflict Detection** | Finds impossible flag combinations using Z3 solver |
| **Dead Code Finder** | Identifies unreachable code paths behind disabled flags |
| **Dependency Graph** | Interactive Mermaid diagram of flag relationships |
| **Health Score** | Calculates project-level flag health (0-100%) |

### Multi-Platform Parsers
| Platform | Format | Status |
|----------|--------|--------|
| LaunchDarkly | JSON | Supported |
| Unleash | YAML/JSON | Supported |
| Custom / Generic | JSON/YAML | Supported |
| Python Source | AST (tree-sitter) | Supported |
| JavaScript Source | AST (tree-sitter) | Supported |

### AI & LLM Integration
- **Ollama** local LLM for conflict explanations
- Plain-English descriptions of why conflicts occur
- Executive summary generation
- AI Chat assistant for interactive analysis (RAG-powered)

### Web Dashboard (Gradio UI)
- **Liquid Glass** design with Royal Obsidian theme (dark/gold aesthetic)
- Interactive charts (Plotly) showing flag status, conflict severity, and health score
- Interactive dependency graph with Mermaid rendering
- File upload for configs and source code archives
- Full analysis report with AI-powered explanations
- Project management (create, switch, analyze per project)
- Login: `admin@example.com` / `admin`
- URL: `http://localhost:7860`

### REST API (FastAPI)
- **31 endpoints** with auto-generated Swagger docs at `/docs`
- JWT authentication with OAuth2 password flow
- Role-Based Access Control (RBAC): `admin > analyst > viewer`
- Full CRUD for Projects, Scans, Environments, Webhooks
- Upload and analyze flag configs programmatically
- Health check endpoints for monitoring
- URL: `http://localhost:8000`

### RBAC (Role-Based Access Control)
| Action | Viewer | Analyst | Admin |
|--------|--------|---------|-------|
| View own projects | Yes | Yes | Yes |
| View all projects | -- | -- | Yes |
| Create projects | -- | Yes | Yes |
| Trigger scans | -- | Yes | Yes |
| Manage webhooks | -- | Yes | Yes |
| Delete resources | -- | -- | Yes |
| Manage users | -- | -- | Yes |

### Multi-Environment Support
- Create `dev`, `staging`, `prod` environments per project
- Set flag overrides per environment
- **Drift detection**: Compare flag states across environments
- Environment-aware scanning

### Webhook & Notification System
- Configure webhook URLs per project for event notifications
- Events: `scan.completed`, `scan.failed`, `conflict.detected`, `flag.created`, `flag.updated`
- HMAC-SHA256 signed payloads for security
- Async dispatch via thread pool (non-blocking)
- Test endpoint to verify webhook connectivity

### Audit Trail
- Immutable audit log for compliance
- Tracks: user actions, resource changes, logins, scans
- Queryable by user, action type, resource, and timestamp

### CLI (Command-Line Interface)
| Command | Description |
|---------|-------------|
| `flagguard analyze` | Full analysis with conflict detection |
| `flagguard parse` | Parse and display flag configuration |
| `flagguard graph` | Generate Mermaid dependency diagram |
| `flagguard check-llm` | Verify Ollama/LLM availability |
| `flagguard init` | Create `.flagguard.yaml` config template |
| `flagguard explain` | Get detailed LLM explanation for a conflict |
| `flagguard scan` | Project-based scan (reads `.flagguard.yaml`) |

### CI/CD Integration
- GitHub Action for automated flag analysis on pull requests
- Block deploys when critical conflicts are detected
- Release workflow for PyPI publishing
- Security scanning workflow

### VS Code Extension
- Syntax highlighting for flag config files
- Inline conflict detection
- Available on VS Code Marketplace

---

## Installation

```bash
pip install flagguard
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add flagguard
```

## Quick Start

### 1. CLI Analysis

```bash
# Analyze your flags
flagguard analyze --config flags.json --source ./src

# Parse and display flags
flagguard parse --config flags.json

# Generate dependency graph
flagguard graph --config flags.json

# Initialize project config
flagguard init

# Project-based scan
flagguard scan --project my-app --save
```

### 2. Web Dashboard

```bash
# Start Gradio UI
uv run python src/flagguard/ui/app.py
# Open http://localhost:7860
# Login: admin@example.com / admin
```

### 3. REST API

```bash
# Start API server
uv run uvicorn flagguard.api.server:app --port 8000
# Open http://localhost:8000/docs for Swagger UI
```

#### API Usage

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123","role":"admin"}'

# Login (get JWT token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@test.com&password=admin123"

# Use token for authenticated requests
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Python API

```python
from flagguard import FlagGuardAnalyzer
from pathlib import Path

analyzer = FlagGuardAnalyzer(explain_with_llm=False)
report = analyzer.analyze(
    config_path=Path("flags.json"),
    source_path=Path("./src"),
    output_format="markdown",
)

print(f"Found {len(report['conflicts'])} conflicts")
```

---

## GitHub Action

Add FlagGuard to your CI pipeline:

```yaml
name: Feature Flag Check
on: [pull_request]

jobs:
  flagguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run FlagGuard
        uses: laxmi2577/flagguard@v1
        with:
          config-path: 'flags/config.json'
          source-path: 'src'
          fail-on-critical: 'true'
```

---

## Architecture

```
flagguard/
|-- api/                  # REST API (FastAPI)
|   |-- server.py         # FastAPI app with Swagger docs
|   |-- auth.py           # JWT auth + RBAC
|   |-- projects.py       # Project CRUD
|   |-- scans.py          # Scan trigger + results
|   |-- flags.py          # Flag parsing + analysis
|   |-- environments.py   # Multi-environment management
|   |-- webhooks.py       # Webhook CRUD + test
|
|-- analysis/             # SAT solver & conflict detection
|   |-- sat_solver.py     # Z3-based SAT solver
|   |-- conflict_detector.py
|   |-- dead_code.py
|
|-- auth/                 # Authentication utilities
|   |-- utils.py          # JWT tokens, password hashing
|
|-- cli/                  # Command-line interface (Click)
|   |-- main.py           # All CLI commands
|
|-- core/                 # Core infrastructure
|   |-- db.py             # SQLAlchemy engine & sessions
|   |-- models/           # Database models (User, Project, Scan, etc.)
|   |-- orchestrator.py   # Analysis pipeline orchestration
|
|-- llm/                  # LLM integration
|   |-- ollama_client.py  # Ollama API client
|   |-- explainer.py      # Conflict explanation generation
|
|-- parsers/              # Config & AST parsers
|   |-- launchdarkly.py   # LaunchDarkly format
|   |-- unleash.py        # Unleash format
|   |-- ast/              # Python/JS source parsing (tree-sitter)
|
|-- rag/                  # RAG for AI chat
|   |-- store.py          # ChromaDB vector store
|   |-- chat.py           # Chat engine
|
|-- reporters/            # Output formatters
|   |-- markdown.py
|   |-- json_reporter.py
|
|-- services/             # Business logic services
|   |-- analysis.py       # Analysis execution service
|   |-- webhooks.py       # Webhook dispatcher (HMAC-signed)
|
|-- ui/                   # Gradio web interface
    |-- app.py            # Dashboard, charts, login
```

---

## Database Models

| Model | Purpose |
|-------|---------|
| **User** | Authentication with RBAC roles (admin/analyst/viewer) |
| **Project** | Represents a codebase being analyzed |
| **Scan** | A single analysis run with status tracking |
| **ScanResult** | Detailed JSON results of a scan |
| **Environment** | Multi-env config (dev/staging/prod) with flag overrides |
| **WebhookConfig** | Webhook URL, events, HMAC secret |
| **AuditLog** | Immutable compliance trail |

---

## API Endpoints

| Group | Endpoints | Key Operations |
|-------|-----------|----------------|
| **Auth** | 5 | Register, Login, Me, List Users, Update User |
| **Projects** | 5 | CRUD + List Scans |
| **Scans** | 3 | Trigger Scan, Get Scan, Get Report |
| **Flags** | 2 | Parse Config, Analyze Conflicts |
| **Environments** | 5 | CRUD + Drift Detection Compare |
| **Webhooks** | 5 | CRUD + Test Webhook |
| **Health** | 2 | Root health + component status |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11+ |
| **SAT Solver** | Z3 (z3-solver) |
| **AST Parsing** | tree-sitter (Python, JavaScript) |
| **Web UI** | Gradio |
| **REST API** | FastAPI + Uvicorn |
| **Database** | SQLite (default) / PostgreSQL |
| **ORM** | SQLAlchemy |
| **Auth** | JWT (python-jose) + passlib |
| **Charts** | Plotly |
| **LLM** | Ollama (local) |
| **RAG** | ChromaDB |
| **CLI** | Click + Rich |
| **CI/CD** | GitHub Actions |
| **Package Manager** | uv |

---

## Development

```bash
# Clone the repository
git clone https://github.com/laxmi2577/flagguard.git
cd flagguard

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/flagguard --cov-report=html

# Start both servers
uv run python src/flagguard/ui/app.py          # Gradio UI on :7860
uv run uvicorn flagguard.api.server:app --port 8000  # API on :8000
```

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md).

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with care for the feature flag community.
