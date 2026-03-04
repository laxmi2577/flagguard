"""Shared UI handler functions — used by both Admin and Analyst dashboards.

Eliminates code duplication for environment management, report generation,
IaC analysis, and lifecycle checks.
"""

from flagguard.core.db import SessionLocal


def create_environment(project_id: str, env_name: str, flag_overrides_json: str, description: str):
    """Create an environment for a project."""
    if not project_id or not env_name:
        return "Project ID and environment name are required."
    try:
        import json
        from flagguard.core.models.tables import Environment
        overrides = json.loads(flag_overrides_json) if flag_overrides_json.strip() else {}
        db = SessionLocal()
        env = Environment(
            project_id=project_id.strip(), name=env_name.strip(),
            flag_overrides=overrides, description=description or ""
        )
        db.add(env)
        db.commit()
        return f"✅ Environment '{env_name}' created."
    except json.JSONDecodeError:
        return "❌ Invalid JSON for flag overrides."
    except Exception as e:
        return f"❌ Error: {e}"


def compare_drift(project_id: str):
    """Compare flag configurations across environments for a project."""
    if not project_id:
        return [{"error": "Enter a project ID"}]
    try:
        from flagguard.core.models.tables import Environment
        db = SessionLocal()
        envs = db.query(Environment).filter(Environment.project_id == project_id.strip()).all()
        if not envs:
            return [{"info": "No environments found for this project."}]
        result = []
        all_flags = set()
        for env in envs:
            for flag_name in (env.flag_overrides or {}).keys():
                all_flags.add(flag_name)
        for flag in sorted(all_flags):
            row = {"flag": flag}
            for env in envs:
                overrides = env.flag_overrides or {}
                row[env.name] = overrides.get(flag, "NOT SET")
            result.append(row)
        return result if result else [{"info": "No flags configured in any environment."}]
    except Exception as e:
        return [{"error": str(e)}]


def generate_report(project_id: str, fmt: str = "markdown"):
    """Generate a report for a project."""
    if not project_id:
        return "Enter a project ID"
    try:
        from flagguard.core.models.tables import Scan
        db = SessionLocal()
        scans = db.query(Scan).filter(Scan.project_id == project_id.strip())\
                  .order_by(Scan.created_at.desc()).limit(10).all()
        if not scans:
            return "No scans found for this project."

        lines = [f"# FlagGuard Report — Project {project_id[:8]}...", ""]
        for s in scans:
            summary = s.result_summary or {}
            lines.append(f"## Scan {s.id[:8]} ({s.created_at})")
            lines.append(f"- Status: {s.status}")
            lines.append(f"- Flags: {summary.get('flag_count', 0)}")
            lines.append(f"- Conflicts: {summary.get('conflict_count', 0)}")
            lines.append(f"- Health: {summary.get('health_score', 'N/A')}%")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def exec_summary(project_id: str):
    """Generate executive summary for a project."""
    if not project_id:
        return [{"error": "Enter project ID"}]
    try:
        from flagguard.core.models.tables import Scan
        db = SessionLocal()
        scans = db.query(Scan).filter(Scan.project_id == project_id.strip())\
                  .order_by(Scan.created_at.desc()).limit(5).all()
        if not scans:
            return [{"info": "No scans found."}]
        latest = scans[0].result_summary or {}
        return [{
            "total_scans": len(scans),
            "latest_health": latest.get("health_score", "N/A"),
            "latest_flags": latest.get("flag_count", 0),
            "latest_conflicts": latest.get("conflict_count", 0),
            "trend": "improving" if len(scans) > 1 and
                     (scans[0].result_summary or {}).get("health_score", 0) >=
                     (scans[-1].result_summary or {}).get("health_score", 0) else "stable"
        }]
    except Exception as e:
        return [{"error": str(e)}]


def analyze_iac(file_content: str, file_type: str = "terraform"):
    """Analyze IaC file for feature flag references."""
    if not file_content:
        return [{"error": "No file content provided"}]
    try:
        import re
        patterns = {
            "terraform": [r'variable\s+"(\w*flag\w*)"', r'feature_flag\s*=\s*"?(\w+)"?'],
            "pulumi": [r'flag[_\s]*name["\s:=]+(\w+)', r'feature[_\s]*(flag|toggle)'],
            "cloudformation": [r'FeatureFlag', r'Toggle'],
        }
        found = []
        for pat in patterns.get(file_type, patterns["terraform"]):
            matches = re.findall(pat, file_content, re.IGNORECASE)
            found.extend(matches)
        return [{"type": file_type, "flags_found": len(found), "flags": found[:20]}]
    except Exception as e:
        return [{"error": str(e)}]


def lifecycle_check(project_id: str):
    """Check flag lifecycle health for a project."""
    if not project_id:
        return [{"error": "Enter project ID"}]
    try:
        from flagguard.core.models.tables import Scan
        db = SessionLocal()
        scans = db.query(Scan).filter(
            Scan.project_id == project_id.strip(),
            Scan.status == "completed"
        ).order_by(Scan.created_at.desc()).limit(5).all()
        if not scans:
            return [{"info": "No completed scans found."}]
        latest = scans[0].result_summary or {}
        flags = latest.get("flag_count", 0)
        conflicts = latest.get("conflict_count", 0)
        return [{
            "total_flags": flags,
            "stale_flags": max(0, flags - conflicts - 5),
            "active_conflicts": conflicts,
            "health": latest.get("health_score", "N/A"),
            "recommendation": "Review stale flags" if flags > 10 else "Looking good",
        }]
    except Exception as e:
        return [{"error": str(e)}]
