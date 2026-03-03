"""Scheduled Scanning & CI/CD Integration API routes."""

import threading
import time
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db, SessionLocal
from flagguard.core.models.tables import Scan, ScanResult, Project, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/scheduler", tags=["Scheduled Scanning"])

# In-memory schedule store (production would use Redis/Celery)
_schedules = {}  # {project_id: {"interval_minutes": int, "active": bool, "last_run": datetime}}
_scheduler_thread = None


# --- Schemas ---
class ScheduleCreate(BaseModel):
    project_id: str
    interval_minutes: int = 60  # Default: every hour
    config_path: str = ""  # Path to flag config on server

class ScheduleOut(BaseModel):
    project_id: str
    interval_minutes: int
    is_active: bool
    last_run: str | None
    next_run: str | None
    total_runs: int

class ScanTrend(BaseModel):
    project_id: str
    trends: list[dict]  # [{date, conflicts, flags, health_score}]
    improvement: float  # % improvement over time

class CICDCheckResult(BaseModel):
    status: str  # pass, fail, warn
    conflicts_found: int
    critical_conflicts: int
    health_score: int
    should_block_merge: bool
    summary: str


# --- Routes ---
@router.post("/schedules", response_model=ScheduleOut)
def create_schedule(
    schedule: ScheduleCreate,
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
    db: Session = Depends(get_db)
):
    """Schedule recurring scans for a project (analyst+ only)."""
    project = db.query(Project).filter(Project.id == schedule.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if schedule.interval_minutes < 5:
        raise HTTPException(status_code=400, detail="Minimum interval is 5 minutes")
    
    _schedules[schedule.project_id] = {
        "interval_minutes": schedule.interval_minutes,
        "active": True,
        "last_run": None,
        "config_path": schedule.config_path,
        "total_runs": 0,
    }
    
    log_action(db, current_user.id, "create", "schedule", schedule.project_id,
               {"interval": schedule.interval_minutes})
    
    # Start background scheduler if not running
    _ensure_scheduler_running()
    
    return _format_schedule(schedule.project_id)


@router.get("/schedules", response_model=list[ScheduleOut])
def list_schedules(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List all active scan schedules."""
    return [_format_schedule(pid) for pid in _schedules]


@router.delete("/schedules/{project_id}")
def delete_schedule(
    project_id: str,
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
    db: Session = Depends(get_db)
):
    """Stop scheduled scanning for a project (analyst+ only)."""
    if project_id in _schedules:
        _schedules[project_id]["active"] = False
        log_action(db, current_user.id, "delete", "schedule", project_id)
        return {"status": "stopped"}
    raise HTTPException(status_code=404, detail="No schedule found for this project")


@router.get("/trends/{project_id}", response_model=ScanTrend)
def get_scan_trends(
    project_id: str,
    days: int = Query(30, description="Number of days to include"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Get conflict trends over time for a project (charts data)."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    scans = (
        db.query(Scan)
        .filter(
            Scan.project_id == project_id,
            Scan.status == "completed",
            Scan.created_at >= cutoff,
        )
        .order_by(Scan.created_at.asc())
        .all()
    )
    
    trends = []
    for scan in scans:
        summary = scan.result_summary or {}
        trends.append({
            "date": str(scan.created_at),
            "scan_id": scan.id,
            "conflicts": summary.get("conflict_count", 0) + summary.get("dependency_count", 0),
            "flags": summary.get("flag_count", 0),
            "health_score": summary.get("health_score", 0),
        })
    
    # Calculate improvement
    improvement = 0.0
    if len(trends) >= 2:
        first_health = trends[0].get("health_score", 0)
        last_health = trends[-1].get("health_score", 0)
        if first_health > 0:
            improvement = round(((last_health - first_health) / first_health) * 100, 1)
    
    return ScanTrend(
        project_id=project_id,
        trends=trends,
        improvement=improvement,
    )


@router.post("/ci-check", response_model=CICDCheckResult)
def ci_cd_check(
    project_id: str = Query(...),
    fail_on_critical: bool = Query(True, description="Return 'fail' status if critical conflicts exist"),
    health_threshold: int = Query(70, description="Minimum health score to pass"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """CI/CD gate check -- use in PR pipelines to block/allow merges."""
    # Get latest scan
    latest_scan = (
        db.query(Scan)
        .filter(Scan.project_id == project_id, Scan.status == "completed")
        .order_by(Scan.created_at.desc())
        .first()
    )
    
    if not latest_scan:
        return CICDCheckResult(
            status="warn",
            conflicts_found=0,
            critical_conflicts=0,
            health_score=0,
            should_block_merge=False,
            summary="No scans found for this project. Run a scan first.",
        )
    
    summary = latest_scan.result_summary or {}
    total_conflicts = summary.get("conflict_count", 0) + summary.get("dependency_count", 0)
    health = summary.get("health_score", 100)
    critical = summary.get("conflict_count", 0)  # Mutual exclusions are critical
    
    # Determine pass/fail
    should_block = False
    status = "pass"
    
    if fail_on_critical and critical > 0:
        status = "fail"
        should_block = True
    elif health < health_threshold:
        status = "warn"
        should_block = False
    
    return CICDCheckResult(
        status=status,
        conflicts_found=total_conflicts,
        critical_conflicts=critical,
        health_score=health,
        should_block_merge=should_block,
        summary=f"Health: {health}% | Conflicts: {total_conflicts} | Critical: {critical}",
    )


# --- Helpers ---
def _format_schedule(project_id: str) -> ScheduleOut:
    sched = _schedules.get(project_id, {})
    last_run = sched.get("last_run")
    interval = sched.get("interval_minutes", 60)
    
    next_run = None
    if last_run and sched.get("active"):
        from datetime import timedelta
        next_dt = last_run + timedelta(minutes=interval)
        next_run = str(next_dt)
    
    return ScheduleOut(
        project_id=project_id,
        interval_minutes=interval,
        is_active=sched.get("active", False),
        last_run=str(last_run) if last_run else None,
        next_run=next_run,
        total_runs=sched.get("total_runs", 0),
    )


def _ensure_scheduler_running():
    """Start the background scheduler thread if not already running."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()


def _scheduler_loop():
    """Background loop that checks and runs scheduled scans."""
    while True:
        for project_id, sched in list(_schedules.items()):
            if not sched.get("active"):
                continue
            
            interval = sched.get("interval_minutes", 60)
            last_run = sched.get("last_run")
            
            from datetime import timedelta
            now = datetime.utcnow()
            
            should_run = last_run is None or (now - last_run) >= timedelta(minutes=interval)
            
            if should_run:
                try:
                    _run_scheduled_scan(project_id, sched.get("config_path", ""))
                    sched["last_run"] = now
                    sched["total_runs"] = sched.get("total_runs", 0) + 1
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Scheduled scan failed for {project_id}: {e}")
        
        time.sleep(30)  # Check every 30 seconds


def _run_scheduled_scan(project_id: str, config_path: str):
    """Execute a scheduled scan."""
    if not config_path:
        return  # Skip if no config path
    
    db = SessionLocal()
    try:
        from flagguard.services.analysis import AnalysisService
        svc = AnalysisService(db)
        scan = svc.run_scan(project_id, config_path)
        scan.triggered_by = "scheduled"
        db.commit()
        
        # Fire webhooks
        try:
            from flagguard.services.webhooks import WebhookDispatcher
            dispatcher = WebhookDispatcher(db)
            dispatcher.dispatch_event("scan.completed", {
                "scan_id": scan.id,
                "project_id": project_id,
                "triggered_by": "scheduled",
                "status": scan.status,
                "summary": scan.result_summary,
            }, project_id)
        except Exception:
            pass
    finally:
        db.close()
