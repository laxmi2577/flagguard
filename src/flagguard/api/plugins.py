"""Plugin Architecture API routes.

Register custom parsers and conflict rules as plugins.
"""

import importlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from flagguard.core.db import get_db
from flagguard.core.models.tables import User
from flagguard.api.auth import get_current_user, require_role, log_action

router = APIRouter(prefix="/plugins", tags=["Plugin Architecture"])

# In-memory plugin registry
_parser_plugins = {
    "launchdarkly": {"name": "LaunchDarkly", "type": "parser", "formats": ["json"], "builtin": True, "active": True},
    "unleash": {"name": "Unleash", "type": "parser", "formats": ["json", "yaml"], "builtin": True, "active": True},
    "generic_json": {"name": "Generic JSON", "type": "parser", "formats": ["json"], "builtin": True, "active": True},
    "generic_yaml": {"name": "Generic YAML", "type": "parser", "formats": ["yaml"], "builtin": True, "active": True},
}

_rule_plugins = {
    "mutual_exclusion": {"name": "Mutual Exclusion Detector", "type": "rule", "severity": "critical", "builtin": True, "active": True},
    "dependency_check": {"name": "Dependency Violation Checker", "type": "rule", "severity": "high", "builtin": True, "active": True},
    "dead_code": {"name": "Dead Code Finder", "type": "rule", "severity": "medium", "builtin": True, "active": True},
    "circular_dependency": {"name": "Circular Dependency Detector", "type": "rule", "severity": "high", "builtin": True, "active": True},
}


# --- Schemas ---
class PluginInfo(BaseModel):
    id: str
    name: str
    type: str  # parser or rule
    builtin: bool
    active: bool
    details: dict

class PluginCreate(BaseModel):
    id: str
    name: str
    type: str  # parser or rule
    module_path: str = ""  # e.g., "my_plugins.custom_parser"
    config: dict = {}

class PluginToggle(BaseModel):
    active: bool


# --- Routes ---
@router.get("", response_model=list[PluginInfo])
def list_plugins(
    plugin_type: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List all registered plugins (parsers and rules)."""
    plugins = []

    for pid, info in _parser_plugins.items():
        if plugin_type and plugin_type != "parser":
            continue
        plugins.append(PluginInfo(id=pid, name=info["name"], type="parser",
                                  builtin=info["builtin"], active=info["active"], details=info))

    for rid, info in _rule_plugins.items():
        if plugin_type and plugin_type != "rule":
            continue
        plugins.append(PluginInfo(id=rid, name=info["name"], type="rule",
                                  builtin=info["builtin"], active=info["active"], details=info))

    return plugins


@router.post("", response_model=PluginInfo)
def register_plugin(
    plugin: PluginCreate,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Register a custom plugin (admin only).

    For parsers: provide a module_path pointing to a class with a parse(filepath) method.
    For rules: provide a module_path pointing to a class with a check(flags) method.
    """
    if plugin.type == "parser":
        if plugin.id in _parser_plugins:
            raise HTTPException(status_code=400, detail=f"Parser plugin '{plugin.id}' already exists")
        _parser_plugins[plugin.id] = {
            "name": plugin.name, "type": "parser", "builtin": False, "active": True,
            "module_path": plugin.module_path, "config": plugin.config,
        }
    elif plugin.type == "rule":
        if plugin.id in _rule_plugins:
            raise HTTPException(status_code=400, detail=f"Rule plugin '{plugin.id}' already exists")
        _rule_plugins[plugin.id] = {
            "name": plugin.name, "type": "rule", "builtin": False, "active": True,
            "module_path": plugin.module_path, "config": plugin.config,
        }
    else:
        raise HTTPException(status_code=400, detail="Type must be 'parser' or 'rule'")

    log_action(db, current_user.id, "create", "plugin", plugin.id, {"name": plugin.name})

    registry = _parser_plugins if plugin.type == "parser" else _rule_plugins
    info = registry[plugin.id]
    return PluginInfo(id=plugin.id, name=info["name"], type=plugin.type,
                      builtin=False, active=True, details=info)


@router.put("/{plugin_id}", response_model=PluginInfo)
def toggle_plugin(
    plugin_id: str,
    toggle: PluginToggle,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Enable or disable a plugin (admin only)."""
    if plugin_id in _parser_plugins:
        _parser_plugins[plugin_id]["active"] = toggle.active
        info = _parser_plugins[plugin_id]
        ptype = "parser"
    elif plugin_id in _rule_plugins:
        _rule_plugins[plugin_id]["active"] = toggle.active
        info = _rule_plugins[plugin_id]
        ptype = "rule"
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

    log_action(db, current_user.id, "update", "plugin", plugin_id,
               {"active": toggle.active})

    return PluginInfo(id=plugin_id, name=info["name"], type=ptype,
                      builtin=info.get("builtin", False), active=toggle.active, details=info)


@router.delete("/{plugin_id}")
def unregister_plugin(
    plugin_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Remove a custom plugin (admin only). Built-in plugins cannot be removed."""
    for registry in [_parser_plugins, _rule_plugins]:
        if plugin_id in registry:
            if registry[plugin_id].get("builtin"):
                raise HTTPException(status_code=400, detail="Cannot remove built-in plugins")
            del registry[plugin_id]
            log_action(db, current_user.id, "delete", "plugin", plugin_id)
            return {"status": "removed"}

    raise HTTPException(status_code=404, detail="Plugin not found")
