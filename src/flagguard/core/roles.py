"""Role enum — single source of truth for role names and hierarchy.

Usage:
    from flagguard.core.roles import Role
    if Role.has_access(user.role, Role.ANALYST):
        ...
"""

from enum import Enum


class Role(str, Enum):
    """Application roles ordered by hierarchy (lowest → highest)."""
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"

    @staticmethod
    def hierarchy() -> dict[str, int]:
        return {
            Role.VIEWER: 0,
            Role.ANALYST: 1,
            Role.ADMIN: 2,
        }

    @classmethod
    def has_access(cls, user_role: str, minimum_role: "Role") -> bool:
        """Check if user_role meets the minimum_role requirement."""
        h = cls.hierarchy()
        return h.get(user_role, 0) >= h.get(minimum_role, 0)

    @classmethod
    def is_valid(cls, role: str) -> bool:
        """Check if a string is a valid role name."""
        return role in {r.value for r in cls}
