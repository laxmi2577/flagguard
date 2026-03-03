"""Environments API routes for multi-environment support."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import Environment, Project, User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/environments", tags=["Environments"])


# --- Schemas ---
class EnvironmentCreate(BaseModel):
    name: str  # dev, staging, prod
    description: str = ""
    flag_overrides: dict = {}
    is_default: bool = False

class EnvironmentOut(BaseModel):
    id: str
    name: str
    project_id: str
    description: str | None
    flag_overrides: dict | None
    is_default: bool
    created_at: str | None

    class Config:
        from_attributes = True

class EnvironmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    flag_overrides: dict | None = None
    is_default: bool | None = None

class EnvCompare(BaseModel):
    environment_a: str
    environment_b: str
    differences: list[dict]


# --- Routes ---
@router.get("/project/{project_id}", response_model=list[EnvironmentOut])
def list_environments(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """List all environments for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Environment).filter(Environment.project_id == project_id).all()


@router.post("/project/{project_id}", response_model=EnvironmentOut)
def create_environment(
    project_id: str,
    env: EnvironmentCreate,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Create a new environment for a project (analyst+ only)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for duplicate name
    existing = db.query(Environment).filter(
        Environment.project_id == project_id,
        Environment.name == env.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Environment '{env.name}' already exists")
    
    new_env = Environment(
        name=env.name,
        project_id=project_id,
        description=env.description,
        flag_overrides=env.flag_overrides,
        is_default=env.is_default,
    )
    db.add(new_env)
    db.commit()
    db.refresh(new_env)
    log_action(db, current_user.id, "create", "environment", new_env.id,
               {"name": env.name, "project_id": project_id})
    return new_env


@router.put("/{env_id}", response_model=EnvironmentOut)
def update_environment(
    env_id: str,
    update: EnvironmentUpdate,
    current_user: Annotated[User, Depends(require_role("analyst"))],
    db: Session = Depends(get_db)
):
    """Update an environment's flag overrides (analyst+ only)."""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    if update.name is not None:
        env.name = update.name
    if update.description is not None:
        env.description = update.description
    if update.flag_overrides is not None:
        env.flag_overrides = update.flag_overrides
    if update.is_default is not None:
        env.is_default = update.is_default
    
    db.commit()
    db.refresh(env)
    log_action(db, current_user.id, "update", "environment", env_id,
               {"changes": update.model_dump(exclude_none=True)})
    return env


@router.delete("/{env_id}")
def delete_environment(
    env_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Delete an environment (admin only)."""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    db.delete(env)
    db.commit()
    log_action(db, current_user.id, "delete", "environment", env_id)
    return {"status": "deleted"}


@router.get("/compare", response_model=EnvCompare)
def compare_environments(
    env_a_id: str,
    env_b_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Compare flag configurations between two environments (drift detection)."""
    env_a = db.query(Environment).filter(Environment.id == env_a_id).first()
    env_b = db.query(Environment).filter(Environment.id == env_b_id).first()
    
    if not env_a or not env_b:
        raise HTTPException(status_code=404, detail="One or both environments not found")
    
    overrides_a = env_a.flag_overrides or {}
    overrides_b = env_b.flag_overrides or {}
    
    all_flags = set(list(overrides_a.keys()) + list(overrides_b.keys()))
    differences = []
    
    for flag in sorted(all_flags):
        val_a = overrides_a.get(flag)
        val_b = overrides_b.get(flag)
        if val_a != val_b:
            differences.append({
                "flag": flag,
                f"{env_a.name}": val_a,
                f"{env_b.name}": val_b,
                "status": "drift" if val_a is not None and val_b is not None else "missing"
            })
    
    return EnvCompare(
        environment_a=env_a.name,
        environment_b=env_b.name,
        differences=differences
    )
