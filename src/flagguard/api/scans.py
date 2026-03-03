"""Scans API routes."""

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import Scan, ScanResult, Project, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/scans", tags=["Scans"])


# --- Schemas ---
class ScanOut(BaseModel):
    id: str
    project_id: str | None
    environment_id: str | None
    triggered_by: str | None
    status: str
    result_summary: dict | None
    created_at: str | None

    class Config:
        from_attributes = True

class ScanResultOut(BaseModel):
    id: str
    scan_id: str
    raw_json: dict | None
    created_at: str | None

    class Config:
        from_attributes = True


# --- Routes ---
@router.post("", response_model=ScanOut)
def trigger_scan(
    project_id: str = Form(...),
    environment_id: str = Form(None),
    config_file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
    db: Session = Depends(get_db)
):
    """Trigger a new analysis scan (analyst+ only)."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Save uploaded config to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=config_file.filename) as tmp:
        content = config_file.file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        from flagguard.services.analysis import AnalysisService
        svc = AnalysisService(db)
        scan = svc.run_scan(project_id, tmp_path)
        
        # Update with environment and trigger info
        scan.environment_id = environment_id
        scan.triggered_by = "api"
        db.commit()
        
        log_action(db, current_user.id, "scan", "scan", scan.id, 
                   {"project_id": project_id, "status": scan.status})
        
        # Fire webhooks
        try:
            from flagguard.services.webhooks import WebhookDispatcher
            dispatcher = WebhookDispatcher(db)
            dispatcher.dispatch_event("scan.completed", {
                "scan_id": scan.id,
                "project_id": project_id,
                "status": scan.status,
                "summary": scan.result_summary
            }, project_id)
        except Exception:
            pass  # Non-blocking
        
        return scan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(
    scan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Get scan details."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/report", response_model=ScanResultOut)
def get_scan_report(
    scan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Get full scan report (detailed JSON)."""
    result = db.query(ScanResult).filter(ScanResult.scan_id == scan_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return result
