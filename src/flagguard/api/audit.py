"""Audit Log API routes for compliance and change history."""

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import AuditLog, User
from flagguard.api.auth import get_current_user, require_role

router = APIRouter(prefix="/audit", tags=["Audit Log"])


# --- Schemas ---
class AuditLogOut(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: str | None

    class Config:
        from_attributes = True

class AuditStats(BaseModel):
    total_events: int
    events_today: int
    top_actions: list[dict]
    top_users: list[dict]


# --- Routes ---
@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    action: str | None = Query(None, description="Filter by action (create, update, delete, scan, login)"),
    resource_type: str | None = Query(None, description="Filter by resource (project, scan, webhook, environment)"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """List audit log entries (admin only). Supports filtering and pagination."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    return query.offset(offset).limit(limit).all()


@router.get("/stats", response_model=AuditStats)
def audit_stats(
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Get audit log statistics (admin only)."""
    from sqlalchemy import func
    
    total = db.query(AuditLog).count()
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(AuditLog).filter(AuditLog.created_at >= today).count()
    
    # Top actions
    action_counts = (
        db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )
    
    # Top users
    user_counts = (
        db.query(AuditLog.user_id, func.count(AuditLog.id).label("count"))
        .filter(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )
    
    return AuditStats(
        total_events=total,
        events_today=today_count,
        top_actions=[{"action": a, "count": c} for a, c in action_counts],
        top_users=[{"user_id": u, "count": c} for u, c in user_counts],
    )


@router.get("/export")
def export_audit_logs(
    format: str = Query("json", description="Export format: json or csv"),
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Export audit logs for compliance reporting (admin only)."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(1000).all()
    
    if format == "csv":
        import io, csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "user_id", "action", "resource_type", "resource_id", "details", "created_at"])
        for log in logs:
            writer.writerow([log.id, log.user_id, log.action, log.resource_type, log.resource_id, str(log.details), str(log.created_at)])
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"}
        )
    
    return [
        {
            "id": l.id, "user_id": l.user_id, "action": l.action,
            "resource_type": l.resource_type, "resource_id": l.resource_id,
            "details": l.details, "created_at": str(l.created_at)
        }
        for l in logs
    ]
