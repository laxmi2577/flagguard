"""Projects API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import Project, Scan, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/projects", tags=["Projects"])


# --- Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    created_at: object | None = None

    class Config:
        from_attributes = True

class ScanSummary(BaseModel):
    id: str
    status: str
    triggered_by: str | None
    result_summary: dict | None
    created_at: object | None = None

    class Config:
        from_attributes = True


# --- Routes ---
@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """List all projects for the current user."""
    if current_user.role == "admin":
        return db.query(Project).all()
    return db.query(Project).filter(Project.owner_id == current_user.id).all()


@router.post("", response_model=ProjectOut)
def create_project(
    project: ProjectCreate,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Create a new project (analyst+ only)."""
    new_project = Project(
        name=project.name,
        description=project.description,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    log_action(db, current_user.id, "create", "project", new_project.id)
    return new_project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Get project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Delete a project (admin only)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    log_action(db, current_user.id, "delete", "project", project_id)
    return {"status": "deleted"}


@router.get("/{project_id}/scans", response_model=list[ScanSummary])
def list_project_scans(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """List all scans for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Scan).filter(Scan.project_id == project_id).order_by(Scan.created_at.desc()).all()
