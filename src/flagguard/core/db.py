"""Database configuration and session management.

Handles setting up the SQLAlchemy engine and session factory.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

# Default to local SQLite if no DATABASE_URL provided
# Use absolute path to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.path.join(BASE_DIR, "flagguard.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# SQLite needs specific connect args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Build engine kwargs based on database type
_engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,        # verify connection is alive before use
    "pool_recycle": 300,          # recycle stale connections every 5 min
    "echo": os.getenv("DEBUG", "False").lower() == "true",
}
# Full connection pooling only for production DBs (not SQLite)
if not DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session (FastAPI dependency).
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from contextlib import contextmanager

@contextmanager
def get_db_session():
    """Context manager for safe DB session usage in UI handlers.
    
    Usage:
        with get_db_session() as db:
            db.query(...)
    
    Automatically closes the session even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and run lightweight migrations.

    1. ``create_all()`` creates any *new* tables (e.g. ``project_members``).
    2. A manual ``ALTER TABLE`` adds ``project_code`` to the existing
       ``projects`` table if it is missing (SQLAlchemy's ``create_all``
       does NOT add columns to tables that already exist).
    3. Existing rows get their UUID prefix as a temporary project_code.
    """
    import flagguard.core.models.tables  # noqa — register all models
    Base.metadata.create_all(bind=engine)

    # ── Migration: add project_code if missing ───────────────────────────
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if inspector.has_table("projects"):
        columns = [c["name"] for c in inspector.get_columns("projects")]
        if "project_code" not in columns:
            print("[MIGRATION] Adding 'project_code' column to projects table...")
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE projects ADD COLUMN project_code TEXT"
                ))
                conn.execute(text(
                    "UPDATE projects SET project_code = UPPER(SUBSTR(id, 1, 8)) "
                    "WHERE project_code IS NULL"
                ))
            print("[MIGRATION] Done — existing projects backfilled with UUID prefix")
