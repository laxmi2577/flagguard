"""FlagGuard REST API Server.

Mounts all API routers and provides OpenAPI/Swagger documentation.
Run: uvicorn flagguard.api.server:app --port 8000
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from flagguard.core.db import engine, Base, SessionLocal
from flagguard.core.models.tables import (
    User, Project, Scan, ScanResult, 
    Environment, WebhookConfig, AuditLog
)

# Create all tables
Base.metadata.create_all(bind=engine)

# --- Rate Limiting Setup ---
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    _has_limiter = True
except ImportError:
    # slowapi not installed — run without rate limiting
    limiter = None
    _has_limiter = False


# --- FastAPI App ---
app = FastAPI(
    title="FlagGuard API",
    description=(
        "Enterprise Feature Flag Intelligence Platform.\n\n"
        "**Features:**\n"
        "- Parse & analyze flag configurations\n"
        "- SAT-solver conflict detection\n"
        "- Multi-environment support with drift detection\n"
        "- Role-based access (admin/analyst/viewer)\n"
        "- Webhook notifications (HMAC-signed)\n"
        "- Audit trail & compliance\n"
        "- Flag lifecycle management (staleness, zombie detection)\n"
        "- Scheduled scanning & CI/CD gate checks\n"
        "- Python SDK\n"
    ),
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter state
if _has_limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — locked to Gradio UI origin (not wildcard)
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:7860,http://127.0.0.1:7860"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Mount Routers ---
from flagguard.api.auth import router as auth_router
from flagguard.api.projects import router as projects_router
from flagguard.api.scans import router as scans_router
from flagguard.api.flags import router as flags_router
from flagguard.api.environments import router as environments_router
from flagguard.api.webhooks import router as webhooks_router
from flagguard.api.audit import router as audit_router
from flagguard.api.lifecycle import router as lifecycle_router
from flagguard.api.scheduler import router as scheduler_router
from flagguard.api.analytics import router as analytics_router
from flagguard.api.reports import router as reports_router
from flagguard.api.plugins import router as plugins_router
from flagguard.api.iac import router as iac_router

# All routes prefixed with /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(flags_router, prefix="/api/v1")
app.include_router(environments_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(lifecycle_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(plugins_router, prefix="/api/v1")
app.include_router(iac_router, prefix="/api/v1")


# --- Health Check ---
@app.get("/", tags=["Health"])
def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "FlagGuard API",
        "version": "2.2.0",
        "docs": "/docs"
    }


@app.get("/api/v1/health", tags=["Health"])
def api_health():
    """Detailed API health check — actually tests DB connectivity."""
    db_status = "error"
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "operational" if db_status == "connected" else "degraded",
        "components": {
            "database": db_status,
            "auth": "ready",
            "webhooks": "ready",
            "analysis_engine": "ready"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
