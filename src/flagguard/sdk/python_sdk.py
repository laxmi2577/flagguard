"""FlagGuard Python SDK.

Usage:
    from flagguard_sdk import FlagGuardClient

    client = FlagGuardClient(base_url="http://localhost:8000", api_key="your_jwt_token")

    # Check project health
    health = client.check_health("project_id")
    print(f"Health: {health['health_score']}%")

    # Run a scan
    result = client.scan("project_id", "path/to/flags.json")

    # Get lifecycle report
    report = client.lifecycle_report("project_id")
    for flag in report['flags']:
        if flag['status'] == 'zombie':
            print(f"  Remove: {flag['name']}")

    # CI/CD gate check
    check = client.ci_check("project_id")
    if check['should_block_merge']:
        sys.exit(1)
"""

import json
import requests
from typing import Optional


class FlagGuardClient:
    """Python SDK for FlagGuard REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session = requests.Session()
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    # --- Authentication ---

    def login(self, email: str, password: str) -> str:
        """Login and store JWT token. Returns the access token."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self.api_key = token
        self._session.headers["Authorization"] = f"Bearer {token}"
        return token

    def register(self, email: str, password: str, role: str = "viewer", full_name: str = "") -> dict:
        """Register a new user."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/auth/register",
            json={"email": email, "password": password, "role": role, "full_name": full_name},
        )
        resp.raise_for_status()
        return resp.json()

    def me(self) -> dict:
        """Get current user profile."""
        resp = self._session.get(f"{self.base_url}/api/v1/auth/me")
        resp.raise_for_status()
        return resp.json()

    # --- Projects ---

    def list_projects(self) -> list[dict]:
        """List all projects."""
        resp = self._session.get(f"{self.base_url}/api/v1/projects")
        resp.raise_for_status()
        return resp.json()

    def create_project(self, name: str, description: str = "") -> dict:
        """Create a new project."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/projects",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json()

    def get_project(self, project_id: str) -> dict:
        """Get project details."""
        resp = self._session.get(f"{self.base_url}/api/v1/projects/{project_id}")
        resp.raise_for_status()
        return resp.json()

    # --- Scans ---

    def scan(self, project_id: str, config_file_path: str, environment_id: str = None) -> dict:
        """Trigger a scan by uploading a config file."""
        with open(config_file_path, "rb") as f:
            data = {"project_id": project_id}
            if environment_id:
                data["environment_id"] = environment_id
            resp = self._session.post(
                f"{self.base_url}/api/v1/scans",
                data=data,
                files={"config_file": f},
            )
        resp.raise_for_status()
        return resp.json()

    def get_scan(self, scan_id: str) -> dict:
        """Get scan details."""
        resp = self._session.get(f"{self.base_url}/api/v1/scans/{scan_id}")
        resp.raise_for_status()
        return resp.json()

    def get_scan_report(self, scan_id: str) -> dict:
        """Get full scan report."""
        resp = self._session.get(f"{self.base_url}/api/v1/scans/{scan_id}/report")
        resp.raise_for_status()
        return resp.json()

    # --- Flags ---

    def analyze_flags(self, config_file_path: str) -> dict:
        """Upload and analyze a flag configuration file."""
        with open(config_file_path, "rb") as f:
            resp = self._session.post(
                f"{self.base_url}/api/v1/flags/analyze",
                files={"config_file": f},
            )
        resp.raise_for_status()
        return resp.json()

    def parse_flags(self, config_file_path: str) -> list[dict]:
        """Parse a flag configuration file."""
        with open(config_file_path, "rb") as f:
            resp = self._session.post(
                f"{self.base_url}/api/v1/flags/parse",
                files={"config_file": f},
            )
        resp.raise_for_status()
        return resp.json()

    # --- Environments ---

    def list_environments(self, project_id: str) -> list[dict]:
        """List environments for a project."""
        resp = self._session.get(f"{self.base_url}/api/v1/environments/project/{project_id}")
        resp.raise_for_status()
        return resp.json()

    def create_environment(self, project_id: str, name: str, flag_overrides: dict = None) -> dict:
        """Create a new environment."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/environments/project/{project_id}",
            json={"name": name, "flag_overrides": flag_overrides or {}},
        )
        resp.raise_for_status()
        return resp.json()

    def compare_environments(self, env_a_id: str, env_b_id: str) -> dict:
        """Compare flag overrides between two environments."""
        resp = self._session.get(
            f"{self.base_url}/api/v1/environments/compare",
            params={"env_a_id": env_a_id, "env_b_id": env_b_id},
        )
        resp.raise_for_status()
        return resp.json()

    # --- Lifecycle ---

    def lifecycle_report(self, project_id: str, stale_threshold_days: int = 30) -> dict:
        """Get flag lifecycle health report."""
        resp = self._session.get(
            f"{self.base_url}/api/v1/lifecycle/report/{project_id}",
            params={"stale_threshold_days": stale_threshold_days},
        )
        resp.raise_for_status()
        return resp.json()

    def cleanup_suggestions(self, project_id: str) -> dict:
        """Get cleanup recommendations for stale/zombie flags."""
        resp = self._session.get(f"{self.base_url}/api/v1/lifecycle/cleanup/{project_id}")
        resp.raise_for_status()
        return resp.json()

    # --- CI/CD ---

    def ci_check(self, project_id: str, fail_on_critical: bool = True, health_threshold: int = 70) -> dict:
        """CI/CD gate check -- returns pass/fail/warn status."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/scheduler/ci-check",
            params={
                "project_id": project_id,
                "fail_on_critical": fail_on_critical,
                "health_threshold": health_threshold,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def scan_trends(self, project_id: str, days: int = 30) -> dict:
        """Get scan trend data for charts."""
        resp = self._session.get(
            f"{self.base_url}/api/v1/scheduler/trends/{project_id}",
            params={"days": days},
        )
        resp.raise_for_status()
        return resp.json()

    # --- Webhooks ---

    def create_webhook(self, project_id: str, url: str, events: list[str] = None) -> dict:
        """Create a webhook."""
        resp = self._session.post(
            f"{self.base_url}/api/v1/webhooks",
            json={
                "project_id": project_id,
                "url": url,
                "events": events or ["scan.completed", "conflict.detected"],
            },
        )
        resp.raise_for_status()
        return resp.json()

    # --- Health ---

    def check_health(self) -> dict:
        """Check API health."""
        resp = self._session.get(f"{self.base_url}/api/v1/health")
        resp.raise_for_status()
        return resp.json()
