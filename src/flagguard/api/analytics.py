"""Dashboard Analytics API routes.

Provides aggregated analytics, health scores, leaderboards,
and chart-ready data for the FlagGuard dashboard.
"""

from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import (
    Scan, ScanResult, Project, User, AuditLog, Environment, WebhookConfig
)
from flagguard.api.auth import get_current_user, require_role

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])


# --- Schemas ---
class PlatformStats(BaseModel):
    total_users: int
    total_projects: int
    total_scans: int
    total_environments: int
    total_webhooks: int
    total_audit_events: int
    avg_health_score: float

class ProjectHealthCard(BaseModel):
    project_id: str
    project_name: str
    owner: str | None
    latest_health: int
    total_scans: int
    total_conflicts: int
    last_scan_date: str | None
    trend: str  # improving, declining, stable

class ConflictTimeline(BaseModel):
    dates: list[str]
    conflicts: list[int]
    health_scores: list[int]
    flag_counts: list[int]

class Leaderboard(BaseModel):
    healthiest_projects: list[dict]
    most_active_users: list[dict]
    most_stale_projects: list[dict]


# --- Routes ---
@router.get("/overview", response_model=PlatformStats)
def platform_overview(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Get platform-wide statistics for the main dashboard."""
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_scans = db.query(Scan).count()
    total_envs = db.query(Environment).count()
    total_webhooks = db.query(WebhookConfig).count()
    total_audit = db.query(AuditLog).count()

    # Average health score from latest scan per project
    latest_scans = (
        db.query(Scan)
        .filter(Scan.status == "completed", Scan.result_summary.isnot(None))
        .order_by(Scan.created_at.desc())
        .limit(50)
        .all()
    )
    health_scores = [
        s.result_summary.get("health_score", 0) 
        for s in latest_scans if s.result_summary
    ]
    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 0

    return PlatformStats(
        total_users=total_users,
        total_projects=total_projects,
        total_scans=total_scans,
        total_environments=total_envs,
        total_webhooks=total_webhooks,
        total_audit_events=total_audit,
        avg_health_score=avg_health,
    )


@router.get("/project-health", response_model=list[ProjectHealthCard])
def project_health_cards(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Get health cards for all projects (dashboard cards)."""
    from sqlalchemy.orm import joinedload
    projects = db.query(Project).options(joinedload(Project.owner)).all()
    cards = []

    for project in projects:
        scans = (
            db.query(Scan)
            .filter(Scan.project_id == project.id, Scan.status == "completed")
            .order_by(Scan.created_at.desc())
            .limit(5)
            .all()
        )

        latest_health = 0
        total_conflicts = 0
        last_scan_date = None
        trend = "stable"

        if scans:
            latest = scans[0]
            summary = latest.result_summary or {}
            latest_health = summary.get("health_score", 0)
            total_conflicts = summary.get("conflict_count", 0) + summary.get("dependency_count", 0)
            last_scan_date = str(latest.created_at)

            # Calculate trend from last 5 scans
            if len(scans) >= 2:
                scores = [
                    (s.result_summary or {}).get("health_score", 0) for s in scans
                ]
                if scores[0] > scores[-1] + 5:
                    trend = "improving"
                elif scores[0] < scores[-1] - 5:
                    trend = "declining"

        owner_name = ""
        if project.owner:
            owner_name = project.owner.full_name or project.owner.email

        cards.append(ProjectHealthCard(
            project_id=project.id,
            project_name=project.name,
            owner=owner_name,
            latest_health=latest_health,
            total_scans=len(scans),
            total_conflicts=total_conflicts,
            last_scan_date=last_scan_date,
            trend=trend,
        ))

    # Sort: worst health first
    cards.sort(key=lambda c: c.latest_health)
    return cards


@router.get("/timeline/{project_id}", response_model=ConflictTimeline)
def conflict_timeline(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Get conflict timeline data for a project (line chart)."""
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

    dates = []
    conflicts = []
    health_scores = []
    flag_counts = []

    for scan in scans:
        summary = scan.result_summary or {}
        dates.append(str(scan.created_at)[:10])
        conflicts.append(summary.get("conflict_count", 0) + summary.get("dependency_count", 0))
        health_scores.append(summary.get("health_score", 0))
        flag_counts.append(summary.get("flag_count", 0))

    return ConflictTimeline(
        dates=dates,
        conflicts=conflicts,
        health_scores=health_scores,
        flag_counts=flag_counts,
    )


@router.get("/leaderboard", response_model=Leaderboard)
def leaderboard(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Get gamified leaderboard: healthiest projects, most active users, most stale."""
    # Healthiest projects
    projects = db.query(Project).all()
    project_health = []
    stale_projects = []

    for p in projects:
        latest = (
            db.query(Scan)
            .filter(Scan.project_id == p.id, Scan.status == "completed")
            .order_by(Scan.created_at.desc())
            .first()
        )
        if latest and latest.result_summary:
            health = latest.result_summary.get("health_score", 0)
            project_health.append({"name": p.name, "health_score": health, "project_id": p.id})

            days_since = (datetime.utcnow() - latest.created_at).days if latest.created_at else 999
            if days_since > 7:
                stale_projects.append({"name": p.name, "days_since_scan": days_since, "project_id": p.id})

    project_health.sort(key=lambda x: -x["health_score"])
    stale_projects.sort(key=lambda x: -x["days_since_scan"])

    # Most active users
    user_counts = (
        db.query(AuditLog.user_id, func.count(AuditLog.id).label("actions"))
        .filter(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )
    active_users = []
    for user_id, count in user_counts:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            active_users.append({
                "name": user.full_name or user.email,
                "actions": count,
                "role": user.role,
            })

    return Leaderboard(
        healthiest_projects=project_health[:10],
        most_active_users=active_users,
        most_stale_projects=stale_projects[:10],
    )
