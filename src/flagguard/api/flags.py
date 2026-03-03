"""Flags API routes."""

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import User
from flagguard.api.auth import get_current_user, require_role

router = APIRouter(prefix="/flags", tags=["Flags"])


# --- Schemas ---
class FlagOut(BaseModel):
    name: str
    enabled: bool
    dependencies: list[str]
    metadata: dict | None = None

class AnalysisRequest(BaseModel):
    format: str = "json"  # json or markdown

class AnalysisResult(BaseModel):
    flags: list[FlagOut]
    conflicts: list[dict]
    health_score: int
    summary: dict


# --- Routes ---
@router.post("/parse", response_model=list[FlagOut])
def parse_flags(
    config_file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Parse a flag configuration file and return structured flags."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=config_file.filename) as tmp:
        content = config_file.file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        from flagguard.parsers import parse_config
        flags = parse_config(Path(tmp_path))
        return [
            FlagOut(
                name=f.name, 
                enabled=f.enabled, 
                dependencies=f.dependencies,
                metadata={"variants": getattr(f, 'variants', []), "source": getattr(f, 'source', '')}
            ) 
            for f in flags
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/analyze", response_model=AnalysisResult)
def analyze_flags(
    config_file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("analyst"))] = None,
):
    """Analyze flag configuration for conflicts and dependencies (analyst+ only)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=config_file.filename) as tmp:
        content = config_file.file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        from flagguard.parsers import parse_config
        from flagguard.analysis import FlagSATSolver, ConflictDetector
        from flagguard.core.models import ConflictType
        
        flags = parse_config(Path(tmp_path))
        
        solver = FlagSATSolver()
        detector = ConflictDetector(solver)
        detector.load_flags(flags)
        conflicts = detector.detect_all_conflicts()
        
        mutual = [c for c in conflicts if c.conflict_type == ConflictType.MUTUAL_EXCLUSION]
        dep_violations = [c for c in conflicts if c.conflict_type == ConflictType.DEPENDENCY_VIOLATION]
        
        total = len(conflicts)
        flag_count = len(flags)
        health = int(max(0, 1 - (total / flag_count if flag_count else 0)) * 100)
        
        return AnalysisResult(
            flags=[FlagOut(name=f.name, enabled=f.enabled, dependencies=f.dependencies) for f in flags],
            conflicts=[c.to_dict() for c in conflicts],
            health_score=health,
            summary={
                "total_flags": flag_count,
                "enabled": sum(1 for f in flags if f.enabled),
                "mutual_exclusions": len(mutual),
                "dependency_violations": len(dep_violations),
                "health_score": health,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
