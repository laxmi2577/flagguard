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

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # Echo SQL in dev mode for debugging
    echo=os.getenv("DEBUG", "False").lower() == "true",
)

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
    """Create all tables on server start (auto-migration).
    
    Safe to call on every startup — SQLAlchemy only creates tables
    that don't exist yet (CREATE TABLE IF NOT EXISTS).
    Covers all models: User, Project, Environment, Scan, FlagDefinition,
    WebhookConfig, AuditLog, PendingUser, Notification, etc.
    """
    import flagguard.core.models.tables  # Ensure all models are loaded into metadata
    Base.metadata.create_all(bind=engine)


# Auto-run migration when this module is imported (server startup)
init_db()

