# FlagGuard API & SDK Reference

FlagGuard can be consumed as a Python SDK, a REST API, or a Command-Line Interface (CLI).

---

## 🐍 Python SDK

Use FlagGuard directly inside your Python applications to integrate static flag analysis into your own tools.

### Initialization & Analysis

```python
from pathlib import Path
from flagguard import FlagGuardAnalyzer

# Initialize analyzer (LLM explanations are optional)
analyzer = FlagGuardAnalyzer(explain_with_llm=False)

# Run full analysis
report = analyzer.analyze(
    config_path=Path("flags.json"),
    source_path=Path("./src"),
)

print(f"Detected {len(report['conflicts'])} conflicts.")
for conflict in report["conflicts"]:
    print(f"[{conflict['severity'].upper()}] {conflict['reason']}")
```

### Manual SAT Solver Usage

Interact directly with the Z3 constraint solver to model complex states.

```python
from flagguard.analysis import FlagSATSolver

solver = FlagSATSolver()
# Model a constraint: premium_feature requires payment_system
solver.add_requires("premium_feature", "payment_system")

# Test if a specific state is mathematically possible
is_possible = solver.check_state_possible({
    "premium_feature": True,
    "payment_system": False,
})
print("Is state possible?", is_possible) # False
```

---

## 🌐 REST API (FastAPI)

For service-to-service communication, run the FlagGuard API server.

```bash
uv run uvicorn flagguard.api.server:app --port 8000
```
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Redoc Viewer: `http://localhost:8000/redoc`

### Core API Workflows

**1. Authentication:**
```bash
# Obtain a JWT Bearer token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=Admin@123"
```

**2. Create a Project:**
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Core Platform", "description": "Backend API"}'
```

**3. Trigger a Scan:**
```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_123", "config_data": {"flags": []}, "source_archive": "base64..."}'
```

---

## 💻 Command Line Interface (CLI)

The easiest way to integrate FlagGuard into CI/CD pipelines.

### `flagguard analyze`
Run a full analysis with conflict detection and dead code finding.
```bash
flagguard analyze --config flags.json --source ./src
flagguard analyze -c flags.json -s ./src --no-llm -o report.json -f json
```

### `flagguard graph`
Generate an interactive Mermaid dependency diagram linking your flags.
```bash
flagguard graph --config flags.json -o deps.mermaid
```

### `flagguard check-llm`
Verify your local Ollama instance is running and has the required `gemma2:2b` model.
```bash
flagguard check-llm
```

### `flagguard scan`
Run a scan tied to a specific project. It automatically looks for a `.flagguard.yaml` configuration file.
```bash
flagguard scan --project my-app --save
```
