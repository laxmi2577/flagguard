"""Plugin Architecture API routes.

Register custom parsers and conflict rules as plugins.
Now persisted to DB via PluginConfig model (survives restarts).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db, SessionLocal
from flagguard.core.models.tables import User, PluginConfig
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/plugins", tags=["Plugin Architecture"])


# Built-in plugins seeded on first access
_BUILTINS = [
    {"id": "launchdarkly", "name": "LaunchDarkly", "type": "parser", "description": "JSON format", "is_builtin": True},
    {"id": "unleash", "name": "Unleash", "type": "parser", "description": "JSON/YAML format", "is_builtin": True},
    {"id": "generic_json", "name": "Generic JSON", "type": "parser", "description": "JSON format", "is_builtin": True},
    {"id": "generic_yaml", "name": "Generic YAML", "type": "parser", "description": "YAML format", "is_builtin": True},
    {"id": "mutual_exclusion", "name": "Mutual Exclusion Detector", "type": "rule", "description": "Critical severity", "is_builtin": True},
    {"id": "dependency_check", "name": "Dependency Violation Checker", "type": "rule", "description": "High severity", "is_builtin": True},
    {"id": "dead_code", "name": "Dead Code Finder", "type": "rule", "description": "Medium severity", "is_builtin": True},
    {"id": "circular_dependency", "name": "Circular Dependency Detector", "type": "rule", "description": "High severity", "is_builtin": True},
]

_seeded = False

def _seed_builtins(db: Session):
    """Seed built-in plugins into DB if they don't exist."""
    global _seeded
    if _seeded:
        return
    for b in _BUILTINS:
        existing = db.query(PluginConfig).filter(PluginConfig.id == b["id"]).first()
        if not existing:
            db.add(PluginConfig(
                id=b["id"], name=b["name"], type=b["type"],
                description=b["description"], is_builtin=True, is_active=True
            ))
    db.commit()
    _seeded = True


# --- Schemas ---
class PluginInfo(BaseModel):
    id: str
    name: str
    type: str  # parser or rule
    builtin: bool
    active: bool
    description: str

class PluginCreate(BaseModel):
    id: str
    name: str
    type: str  # parser or rule
    description: str = ""
    config: dict = {}

class PluginToggle(BaseModel):
    active: bool


# --- Routes ---
@router.get("", response_model=list[PluginInfo])
def list_plugins(
    plugin_type: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """List all registered plugins (parsers and rules)."""
    _seed_builtins(db)
    
    query = db.query(PluginConfig)
    if plugin_type:
        query = query.filter(PluginConfig.type == plugin_type)
    
    plugins = query.all()
    return [PluginInfo(
        id=p.id, name=p.name, type=p.type,
        builtin=p.is_builtin, active=p.is_active,
        description=p.description or ""
    ) for p in plugins]


@router.post("", response_model=PluginInfo)
def register_plugin(
    plugin: PluginCreate,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Register a custom plugin (admin only)."""
    if plugin.type not in ("parser", "rule"):
        raise HTTPException(status_code=400, detail="Type must be 'parser' or 'rule'")
    
    existing = db.query(PluginConfig).filter(PluginConfig.id == plugin.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin.id}' already exists")
    
    new_plugin = PluginConfig(
        id=plugin.id, name=plugin.name, type=plugin.type,
        description=plugin.description, config=plugin.config,
        is_builtin=False, is_active=True
    )
    db.add(new_plugin)
    db.commit()
    db.refresh(new_plugin)
    
    log_action(db, current_user.id, "create", "plugin", plugin.id, {"name": plugin.name})
    
    return PluginInfo(
        id=new_plugin.id, name=new_plugin.name, type=new_plugin.type,
        builtin=False, active=True, description=new_plugin.description or ""
    )


@router.put("/{plugin_id}", response_model=PluginInfo)
def toggle_plugin(
    plugin_id: str,
    toggle: PluginToggle,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Enable or disable a plugin (admin only)."""
    plugin = db.query(PluginConfig).filter(PluginConfig.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    plugin.is_active = toggle.active
    db.commit()
    
    log_action(db, current_user.id, "update", "plugin", plugin_id, {"active": toggle.active})
    
    return PluginInfo(
        id=plugin.id, name=plugin.name, type=plugin.type,
        builtin=plugin.is_builtin, active=plugin.is_active,
        description=plugin.description or ""
    )


@router.delete("/{plugin_id}")
def unregister_plugin(
    plugin_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Remove a custom plugin (admin only). Built-in plugins cannot be removed."""
    plugin = db.query(PluginConfig).filter(PluginConfig.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if plugin.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot remove built-in plugins")
    
    db.delete(plugin)
    db.commit()
    log_action(db, current_user.id, "delete", "plugin", plugin_id)
    return {"status": "removed"}
