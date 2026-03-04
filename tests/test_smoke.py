"""Smoke Test — Verify app starts without errors."""

import pytest


class TestSmoke:
    def test_api_app_creates(self):
        """FastAPI app should create without errors."""
        from flagguard.api.server import app
        assert app is not None
        assert app.title == "FlagGuard API"

    def test_ui_app_creates(self):
        """Gradio app should create without errors."""
        from flagguard.ui.app import create_app
        app = create_app()
        assert app is not None

    def test_db_initializes(self):
        """Database should initialize and create tables."""
        from flagguard.core.db import engine, Base
        from flagguard.core.models.tables import User, Project, Scan
        
        Base.metadata.create_all(bind=engine)
        # Check tables exist
        table_names = list(Base.metadata.tables.keys())
        assert "users" in table_names
        assert "projects" in table_names
        assert "scans" in table_names

    def test_roles_enum(self):
        """Role enum should have correct hierarchy."""
        from flagguard.core.roles import Role
        
        assert Role.has_access("admin", Role.ADMIN)
        assert Role.has_access("admin", Role.VIEWER)
        assert not Role.has_access("viewer", Role.ADMIN)
        assert Role.has_access("analyst", Role.ANALYST)
        assert Role.is_valid("admin")
        assert not Role.is_valid("superuser")
