"""API Test Suite — Auth + CRUD tests for FlagGuard API.

Tests the 13 API routers with actual HTTP calls using FastAPI's TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from flagguard.api.server import app
from flagguard.core.db import SessionLocal, engine, Base


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Register an admin user and return the auth token."""
    client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "Admin123",
        "full_name": "Test Admin",
        "role": "admin"
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "admin@test.com", "password": "Admin123"
    })
    return resp.json()["access_token"]


@pytest.fixture
def auth_header(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Auth Tests ──────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_user(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "viewer@test.com",
            "password": "Viewer123",
            "full_name": "Test Viewer",
            "role": "viewer"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "viewer@test.com"
        assert data["role"] == "viewer"

    def test_duplicate_email_rejected(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "password": "DupTest123",
            "full_name": "Dup User", "role": "viewer"
        })
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "password": "DupTest123",
            "full_name": "Dup User 2", "role": "viewer"
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_login_success(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "login@test.com", "password": "Login123",
            "full_name": "Login User", "role": "viewer"
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": "login@test.com", "password": "Login123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "wrong@test.com", "password": "Wrong123",
            "full_name": "Wrong User", "role": "viewer"
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": "wrong@test.com", "password": "BADPass1"
        })
        assert resp.status_code == 401

    def test_get_me(self, client, auth_header):
        resp = client.get("/api/v1/auth/me", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@test.com"

    def test_unauthorized_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ─── Project CRUD Tests ─────────────────────────────────────────────────────

class TestProjects:
    def test_create_project(self, client, auth_header):
        resp = client.post("/api/v1/projects", headers=auth_header, json={
            "name": "Test Project", "description": "A test project"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_list_projects(self, client, auth_header):
        client.post("/api/v1/projects", headers=auth_header, json={
            "name": "Project A", "description": "First"
        })
        client.post("/api/v1/projects", headers=auth_header, json={
            "name": "Project B", "description": "Second"
        })
        resp = client.get("/api/v1/projects", headers=auth_header)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


# ─── RBAC Tests ──────────────────────────────────────────────────────────────

class TestRBAC:
    def test_viewer_cannot_list_users(self, client):
        """Viewers should not have admin access."""
        client.post("/api/v1/auth/register", json={
            "email": "viewer_rbac@test.com", "password": "Viewer123",
            "full_name": "RBAC Viewer", "role": "viewer"
        })
        login_resp = client.post("/api/v1/auth/login", data={
            "username": "viewer_rbac@test.com", "password": "Viewer123"
        })
        token = login_resp.json()["access_token"]

        resp = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client, auth_header):
        resp = client.get("/api/v1/auth/users", headers=auth_header)
        assert resp.status_code == 200


# ─── Health Check Tests ──────────────────────────────────────────────────────

class TestHealth:
    def test_root_health(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_api_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["components"]["database"] == "connected"
