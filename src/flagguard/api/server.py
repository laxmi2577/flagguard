"""FlagGuard REST API Server.

Mounts all API routers and provides OpenAPI/Swagger documentation.
Run: uvicorn flagguard.api.server:app --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flagguard.core.db import engine, Base
from flagguard.core.models.tables import (
    User, Project, Scan, ScanResult, 
    Environment, WebhookConfig, AuditLog
)

# Create all tables
Base.metadata.create_all(bind=engine)

# --- FastAPI App ---
app = FastAPI(
    title="FlagGuard API",
    description=(
        "Enterprise Feature Flag Intelligence Platform.\n\n"
        "**Features:**\n"
        "- 🔍 Parse & analyze flag configurations\n"
        "- ⚡ SAT-solver conflict detection\n"
        "- 🌍 Multi-environment support\n"
        "- 🔐 Role-based access (admin/analyst/viewer)\n"
        "- 🪝 Webhook notifications\n"
        "- 📊 Audit trail & compliance\n"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
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

# All routes prefixed with /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(flags_router, prefix="/api/v1")
app.include_router(environments_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")


# --- Health Check ---
@app.get("/", tags=["Health"])
def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "FlagGuard API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/api/v1/health", tags=["Health"])
def api_health():
    """Detailed API health check."""
    return {
        "status": "operational",
        "components": {
            "database": "connected",
            "auth": "ready",
            "webhooks": "ready",
            "analysis_engine": "ready"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
