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

from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_logger")

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log before processing
        method = request.method
        url = request.url.path
        if method in ["POST", "PUT", "DELETE"]:
            logger.info(f"AUDIT INVOKED: Method={method} URL={url} IP={request.client.host}")
            
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log after processing
        if method in ["POST", "PUT", "DELETE"]:
            logger.info(f"AUDIT COMPLETED: Method={method} URL={url} Status={response.status_code} Duration={process_time:.4f}s")
        
        return response

app.add_middleware(AuditMiddleware)

# --- Static file serving for fg-modals.js ---
from starlette.staticfiles import StaticFiles
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
_static_dir = os.path.normpath(_static_dir)
app.mount("/fg-static", StaticFiles(directory=_static_dir), name="fg-static")

# --- Script Injection Middleware ---
# Injects <script src="/fg-static/fg-modals.js"> into every HTML response.
# This is the ONLY reliable way to run JS in a Gradio 4+ app because:
#   - gr.HTML() strips <script> tags (DOMPurify)
#   - gr.HTML() strips onclick/onmouseover handlers (DOMPurify)
#   - gr.Blocks(head=...) may not work with gr.mount_gradio_app()
from starlette.responses import Response

class ScriptInjectionMiddleware(BaseHTTPMiddleware):
    SCRIPT_TAG = b'<script src="/fg-static/fg-modals.js"></script>'

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body += chunk.encode("utf-8")
                else:
                    body += chunk
            # Inject script before </head>
            body = body.replace(b"</head>", self.SCRIPT_TAG + b"\n</head>", 1)
            # Build new headers WITHOUT content-length (it changed)
            new_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ("content-length", "content-encoding")
            }
            return Response(
                content=body,
                status_code=response.status_code,
                headers=new_headers,
                media_type="text/html",
            )
        return response

app.add_middleware(ScriptInjectionMiddleware)

# --- Cookie Consent Backend Enforcement ---
class CookieConsentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extremely basic enforcement logic
        consent = request.cookies.get("flagguard_consent")
        if consent == "rejected" and request.url.path.startswith("/api/v1/analytics"):
            return JSONResponse(status_code=403, content={"error": "Consent required for analytics"})
        return await call_next(request)

app.add_middleware(CookieConsentMiddleware)


# --- GDPR Consent Logging Endpoint ---
from pydantic import BaseModel

class ConsentRequest(BaseModel):
    type: str  # "accepted", "rejected", "essential"

@app.post("/api/v1/consent")
async def log_consent(body: ConsentRequest, request: Request):
    """Log verifiable proof of user cookie consent (GDPR Art.7)."""
    try:
        from flagguard.core.db import SessionLocal
        from flagguard.core.models.tables import ConsentLog
        db = SessionLocal()
        log = ConsentLog(
            user_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
            consent_type=body.type,
            consent_version="1.0",
        )
        db.add(log)
        db.commit()
        db.close()
        return {"status": "ok", "consent": body.type}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- Legal Document Serving ---
import re as _re

def _md_to_html(md_text):
    """Convert markdown to basic HTML without external libraries."""
    html = md_text
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = _re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=_re.MULTILINE)
    html = _re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = _re.sub(r'^---+$', r'<hr/>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^\*   (.+)$', r'<li>\1</li>', html, flags=_re.MULTILINE)
    html = _re.sub(r'^\d+\.\s+(.+)$', r'<li>\1</li>', html, flags=_re.MULTILINE)
    html = _re.sub(r'`(.+?)`', r'<code>\1</code>', html)
    html = _re.sub(r'\n\n+', r'</p><p>', html)
    html = f"<p>{html}</p>"
    html = html.replace("<p></p>", "").replace("<p><h", "<h")
    html = html.replace("</h1></p>", "</h1>").replace("</h2></p>", "</h2>")
    html = html.replace("</h3></p>", "</h3>").replace("</hr/></p>", "</hr/>")
    return html

_LEGAL_DOCS = {
    "privacy": "privacy_policy",
    "terms": "terms_of_service",
    "aup": "acceptable_use",
    "accessibility": "accessibility_statement",
    "ai": "ai_transparency",
    "data": "data_inventory",
}

@app.get("/api/v1/legal/{doc_key}")
async def get_legal_doc(doc_key: str):
    """Serve legal documents as HTML for the modal reader."""
    filename = _LEGAL_DOCS.get(doc_key)
    if not filename:
        return JSONResponse(status_code=404, content={"error": "Document not found"})
    import os
    # server.py is at src/flagguard/api/server.py → project root is 4 dirs up
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    path = os.path.join(project_root, "docs", "legal", f"{filename}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            md = f.read()
        html = _md_to_html(md)
        from starlette.responses import HTMLResponse
        return HTMLResponse(content=html)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": f"File not found: {filename}.md"})

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
from flagguard.api.risk import router as risk_router

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
app.include_router(risk_router, prefix="/api/v1")


# --- Health Check ---
@app.get("/health", tags=["Health"])
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
