"""Database models for FlagGuard."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from flagguard.core.db import Base


def generate_uuid() -> str:
    """Generate a unique ID."""
    return uuid.uuid4().hex


# --- RBAC ---

class User(Base):
    """User model with role-based access control."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="viewer")  # admin, analyst, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


class Project(Base):
    """Project model represents a codebase or application being analyzed."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    scans = relationship("Scan", back_populates="project")
    environments = relationship("Environment", back_populates="project")
    webhooks = relationship("WebhookConfig", back_populates="project")


class Scan(Base):
    """Scan model represents a single analysis run."""
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"))
    environment_id = Column(String, ForeignKey("environments.id"), nullable=True)
    triggered_by = Column(String)  # 'manual', 'api', 'webhook', 'scheduled'
    status = Column(String, default="pending")  # pending, running, completed, failed
    result_summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scans")
    environment = relationship("Environment")
    result = relationship("ScanResult", back_populates="scan", uselist=False)


class ScanResult(Base):
    """Detailed results of a scan (stored as heavy JSON)."""
    __tablename__ = "scan_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), unique=True)
    raw_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="result")


# --- Multi-Environment ---

class Environment(Base):
    """Environment configuration (dev, staging, prod)."""
    __tablename__ = "environments"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # dev, staging, prod
    project_id = Column(String, ForeignKey("projects.id"))
    flag_overrides = Column(JSON, default=dict)  # {flag_name: {enabled: bool, ...}}
    description = Column(String, default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="environments")


# --- Webhooks ---

class WebhookConfig(Base):
    """Webhook configuration for notifications."""
    __tablename__ = "webhook_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"))
    url = Column(String, nullable=False)
    secret = Column(String, nullable=True)  # HMAC signing secret
    events = Column(JSON, default=list)  # ["scan.completed", "conflict.detected"]
    is_active = Column(Boolean, default=True)
    description = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="webhooks")


# --- Audit Log ---

class AuditLog(Base):
    """Immutable audit trail for compliance."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # create, update, delete, scan, login
    resource_type = Column(String)  # project, scan, flag, webhook, environment
    resource_id = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
