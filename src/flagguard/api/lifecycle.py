"""Flag Lifecycle Management API routes.

Tracks flag age, staleness, and generates cleanup recommendations.
"""

from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import Scan, ScanResult, Project, User
from flagguard.api.auth import get_current_user, require_role

router = APIRouter(prefix="/lifecycle", tags=["Flag Lifecycle"])


# --- Schemas ---
class FlagHealth(BaseModel):
    name: str
    enabled: bool
    age_days: int
    last_seen_in_scan: str | None
    staleness_score: int  # 0-100 (100 = very stale)
    status: str  # active, stale, zombie, new
    recommendation: str

class LifecycleReport(BaseModel):
    project_id: str
    total_flags: int
    active_flags: int
    stale_flags: int
    zombie_flags: int
    avg_age_days: float
    flags: list[FlagHealth]
    cleanup_suggestions: list[str]

class CleanupPR(BaseModel):
    project_id: str
    flags_to_remove: list[str]
    estimated_dead_code_lines: int
    cleanup_commands: list[str]


# --- Routes ---
@router.get("/report/{project_id}", response_model=LifecycleReport)
def get_lifecycle_report(
    project_id: str,
    stale_threshold_days: int = Query(30, description="Days before a flag is considered stale"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Generate a lifecycle health report for all flags in a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all scans for this project, sorted by newest first
    scans = (
        db.query(Scan)
        .filter(Scan.project_id == project_id, Scan.status == "completed")
        .order_by(Scan.created_at.desc())
        .all()
    )
    
    if not scans:
        return LifecycleReport(
            project_id=project_id, total_flags=0, active_flags=0,
            stale_flags=0, zombie_flags=0, avg_age_days=0,
            flags=[], cleanup_suggestions=["No scans found. Run your first scan!"]
        )
    
    # Collect flag data across all scans
    flag_history = {}  # {flag_name: {first_seen, last_seen, enabled, scan_count}}
    
    for scan in scans:
        result = db.query(ScanResult).filter(ScanResult.scan_id == scan.id).first()
        if not result or not result.raw_json:
            continue
        
        raw = result.raw_json
        flags_list = raw.get("flags", [])
        
        for flag_entry in flags_list:
            name = flag_entry if isinstance(flag_entry, str) else flag_entry.get("name", str(flag_entry))
            
            if name not in flag_history:
                flag_history[name] = {
                    "first_seen": scan.created_at,
                    "last_seen": scan.created_at,
                    "enabled": True,
                    "scan_count": 0,
                }
            
            flag_history[name]["last_seen"] = max(
                flag_history[name]["last_seen"], scan.created_at or datetime.utcnow()
            )
            flag_history[name]["first_seen"] = min(
                flag_history[name]["first_seen"], scan.created_at or datetime.utcnow()
            )
            flag_history[name]["scan_count"] += 1
    
    # Analyze each flag
    now = datetime.utcnow()
    flags = []
    active_count = 0
    stale_count = 0
    zombie_count = 0
    total_age = 0
    
    for name, history in flag_history.items():
        age_days = (now - history["first_seen"]).days if history["first_seen"] else 0
        days_since_seen = (now - history["last_seen"]).days if history["last_seen"] else 0
        total_age += age_days
        
        # Calculate staleness score (0-100)
        staleness = min(100, int((days_since_seen / max(stale_threshold_days, 1)) * 100))
        
        # Determine status
        if days_since_seen > stale_threshold_days * 3:
            status = "zombie"
            zombie_count += 1
            recommendation = f"REMOVE: Flag '{name}' has not appeared in {days_since_seen} days. Likely dead code."
        elif days_since_seen > stale_threshold_days:
            status = "stale"
            stale_count += 1
            recommendation = f"REVIEW: Flag '{name}' hasn't been seen in {days_since_seen} days. Consider removing."
        elif age_days < 7:
            status = "new"
            active_count += 1
            recommendation = f"NEW: Flag '{name}' was added {age_days} days ago. Monitor for conflicts."
        else:
            status = "active"
            active_count += 1
            recommendation = f"OK: Flag '{name}' is healthy ({age_days} days old, seen recently)."
        
        flags.append(FlagHealth(
            name=name,
            enabled=history["enabled"],
            age_days=age_days,
            last_seen_in_scan=str(history["last_seen"]) if history["last_seen"] else None,
            staleness_score=staleness,
            status=status,
            recommendation=recommendation,
        ))
    
    # Sort: zombies first, then stale, then by staleness score
    flags.sort(key=lambda f: (-f.staleness_score, f.name))
    
    # Generate cleanup suggestions
    suggestions = []
    if zombie_count > 0:
        zombie_names = [f.name for f in flags if f.status == "zombie"]
        suggestions.append(f"Remove {zombie_count} zombie flag(s): {', '.join(zombie_names[:5])}")
    if stale_count > 0:
        suggestions.append(f"Review {stale_count} stale flag(s) -- no activity in {stale_threshold_days}+ days")
    if len(flag_history) > 50:
        suggestions.append(f"High flag count ({len(flag_history)}). Consider flag consolidation.")
    avg_age = total_age / len(flag_history) if flag_history else 0
    if avg_age > 90:
        suggestions.append(f"Average flag age is {avg_age:.0f} days. Schedule regular flag reviews.")
    if not suggestions:
        suggestions.append("All flags are healthy! No cleanup needed.")
    
    return LifecycleReport(
        project_id=project_id,
        total_flags=len(flag_history),
        active_flags=active_count,
        stale_flags=stale_count,
        zombie_flags=zombie_count,
        avg_age_days=round(avg_age, 1),
        flags=flags,
        cleanup_suggestions=suggestions,
    )


@router.get("/cleanup/{project_id}", response_model=CleanupPR)
def generate_cleanup(
    project_id: str,
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
    db: Session = Depends(get_db)
):
    """Generate cleanup recommendations for stale/zombie flags (analyst+ only)."""
    # Get the lifecycle report first
    report = get_lifecycle_report(project_id, 30, current_user, db)
    
    zombie_flags = [f.name for f in report.flags if f.status == "zombie"]
    stale_flags = [f.name for f in report.flags if f.status == "stale"]
    flags_to_remove = zombie_flags + stale_flags
    
    commands = []
    for flag in flags_to_remove[:10]:  # Limit to top 10
        commands.append(f"# Remove flag '{flag}' from config and source code")
        commands.append(f"grep -r '{flag}' src/ --include='*.py' --include='*.js'")
    
    return CleanupPR(
        project_id=project_id,
        flags_to_remove=flags_to_remove,
        estimated_dead_code_lines=len(flags_to_remove) * 15,  # Rough estimate
        cleanup_commands=commands,
    )
