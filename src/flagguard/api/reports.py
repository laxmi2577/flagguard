"""Export & Reporting API routes.

Generate PDF executive reports, CSV data exports, and scheduled email reports.
"""

import io
import csv
import json
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import Scan, ScanResult, Project, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/reports", tags=["Export & Reporting"])


# --- Schemas ---
class ReportConfig(BaseModel):
    project_id: str
    format: str = "json"  # json, csv, markdown, html
    include_details: bool = True
    include_recommendations: bool = True

class ReportOut(BaseModel):
    project_name: str
    generated_at: str
    format: str
    summary: dict
    flags: list[dict]
    conflicts: list[dict]
    recommendations: list[str]


# --- Routes ---
@router.post("/generate", response_model=ReportOut)
def generate_report(
    config: ReportConfig,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Generate a comprehensive analysis report for a project."""
    project = db.query(Project).filter(Project.id == config.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get latest completed scan
    latest_scan = (
        db.query(Scan)
        .filter(Scan.project_id == config.project_id, Scan.status == "completed")
        .order_by(Scan.created_at.desc())
        .first()
    )

    if not latest_scan:
        raise HTTPException(status_code=404, detail="No completed scans found. Run a scan first.")

    summary = latest_scan.result_summary or {}

    # Get detailed results
    flags = []
    conflicts = []
    if config.include_details:
        result = db.query(ScanResult).filter(ScanResult.scan_id == latest_scan.id).first()
        if result and result.raw_json:
            raw = result.raw_json
            flags = raw.get("flags", [])
            if isinstance(flags, list) and flags and isinstance(flags[0], str):
                flags = [{"name": f, "enabled": True} for f in flags]
            conflicts = raw.get("conflicts", [])

    # Generate recommendations
    recommendations = []
    if config.include_recommendations:
        health = summary.get("health_score", 100)
        conflict_count = summary.get("conflict_count", 0)
        dep_count = summary.get("dependency_count", 0)

        if health < 50:
            recommendations.append("CRITICAL: Health score below 50%. Immediate conflict resolution needed.")
        elif health < 75:
            recommendations.append("WARNING: Health score below 75%. Review flagged conflicts soon.")
        else:
            recommendations.append("GOOD: Health score is healthy. Continue monitoring.")

        if conflict_count > 0:
            recommendations.append(f"Resolve {conflict_count} mutual exclusion conflict(s) -- these can cause crashes.")
        if dep_count > 0:
            recommendations.append(f"Fix {dep_count} dependency violation(s) -- missing prerequisites detected.")
        if summary.get("flag_count", 0) > 50:
            recommendations.append("Consider flag consolidation -- high flag count increases complexity.")

    log_action(db, current_user.id, "export", "report", config.project_id,
               {"format": config.format})

    return ReportOut(
        project_name=project.name,
        generated_at=str(datetime.utcnow()),
        format=config.format,
        summary=summary,
        flags=flags if isinstance(flags, list) else [],
        conflicts=conflicts,
        recommendations=recommendations,
    )


@router.get("/download/{project_id}")
def download_report(
    project_id: str,
    format: str = Query("csv", description="Export format: csv, json, markdown"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Download a project report as CSV, JSON, or Markdown."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all completed scans
    scans = (
        db.query(Scan)
        .filter(Scan.project_id == project_id, Scan.status == "completed")
        .order_by(Scan.created_at.desc())
        .limit(100)
        .all()
    )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Scan ID", "Date", "Status", "Flags", "Conflicts", "Dependencies", "Health Score"])
        for scan in scans:
            s = scan.result_summary or {}
            writer.writerow([
                scan.id, str(scan.created_at), scan.status,
                s.get("flag_count", 0), s.get("conflict_count", 0),
                s.get("dependency_count", 0), s.get("health_score", 0)
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={project.name}_report.csv"}
        )

    elif format == "markdown":
        lines = [
            f"# FlagGuard Report: {project.name}",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Scan History",
            "| Date | Flags | Conflicts | Health |",
            "|------|-------|-----------|--------|",
        ]
        for scan in scans[:20]:
            s = scan.result_summary or {}
            lines.append(
                f"| {str(scan.created_at)[:10]} | {s.get('flag_count', 0)} | "
                f"{s.get('conflict_count', 0)} | {s.get('health_score', 0)}% |"
            )
        content = "\n".join(lines)
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={project.name}_report.md"}
        )

    else:  # JSON
        data = {
            "project": project.name,
            "generated_at": str(datetime.utcnow()),
            "scans": [
                {
                    "id": s.id, "date": str(s.created_at), "status": s.status,
                    "summary": s.result_summary
                }
                for s in scans
            ]
        }
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={project.name}_report.json"}
        )


@router.get("/executive-summary/{project_id}")
def executive_summary(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """Generate a high-level executive summary for stakeholders."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scans = (
        db.query(Scan)
        .filter(Scan.project_id == project_id, Scan.status == "completed")
        .order_by(Scan.created_at.desc())
        .limit(10)
        .all()
    )

    if not scans:
        return {"summary": "No scan data available. Run your first scan to generate insights."}

    latest = scans[0].result_summary or {}
    health = latest.get("health_score", 0)
    flags = latest.get("flag_count", 0)
    conflicts = latest.get("conflict_count", 0)

    # Trend analysis
    trend_text = "No trend data"
    if len(scans) >= 2:
        prev_health = (scans[-1].result_summary or {}).get("health_score", 0)
        diff = health - prev_health
        if diff > 0:
            trend_text = f"Improving (+{diff}% over last {len(scans)} scans)"
        elif diff < 0:
            trend_text = f"Declining ({diff}% over last {len(scans)} scans)"
        else:
            trend_text = "Stable"

    risk_level = "LOW" if health >= 80 else "MEDIUM" if health >= 50 else "HIGH"

    return {
        "project": project.name,
        "date": str(datetime.utcnow())[:10],
        "risk_level": risk_level,
        "health_score": f"{health}%",
        "total_flags": flags,
        "active_conflicts": conflicts,
        "trend": trend_text,
        "total_scans": len(scans),
        "recommendation": (
            "All clear. Continue monitoring." if risk_level == "LOW"
            else "Review and resolve conflicts before next release." if risk_level == "MEDIUM"
            else "URGENT: Critical conflicts detected. Do not deploy without resolution."
        )
    }
