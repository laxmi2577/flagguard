"""Initialize database."""

from flagguard.core.db import engine, Base, SessionLocal
from flagguard.core.models.tables import User
from flagguard.auth.utils import get_password_hash

def init_db():
    """Initialize DB and create test user."""
    # Create tables (for dev/test without alembic)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if admin exists
    admin_email = "admin@example.com"
    existing_user = db.query(User).filter(User.email == admin_email).first()
    
    if not existing_user:
        print(f"Creating admin user: {admin_email}")
        user = User(
            email=admin_email,
            hashed_password=get_password_hash("Admin@123"),
            full_name="Admin User",
            role="admin",        # ← CRITICAL: must set explicitly (default is 'viewer')
            is_active=True
        )
        db.add(user)
        db.commit()
    else:
        print("Admin user already exists")
        
    db.close()

if __name__ == "__main__":
    init_db()
