"""Authentication API routes with RBAC."""

from datetime import timedelta
from typing import Annotated
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from flagguard.core.db import get_db
from flagguard.core.models.tables import User, AuditLog
from flagguard.auth.utils import verify_password, get_password_hash, create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# --- Role Hierarchy ---
ROLE_HIERARCHY = {"admin": 3, "analyst": 2, "viewer": 1}


# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "viewer"

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# --- Dependencies ---
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    return user


def require_role(minimum_role: str):
    """Dependency that enforces minimum role level."""
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]):
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{minimum_role}' role or higher. Your role: '{current_user.role}'"
            )
        return current_user
    return role_checker


def log_action(db: Session, user_id: str, action: str, resource_type: str = None, 
               resource_id: str = None, details: dict = None):
    """Log an action to the audit trail."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {}
    )
    db.add(entry)
    db.commit()


# --- Routes ---
@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role if user.role in ROLE_HIERARCHY else "viewer"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_action(db, new_user.id, "register", "user", new_user.id)
    return new_user


@router.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    """Login and receive JWT token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=timedelta(minutes=60)
    )
    log_action(db, user.id, "login", "user", user.id)
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user profile."""
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    return db.query(User).all()


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    update: UserUpdate,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Update a user's role or status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if update.full_name is not None:
        user.full_name = update.full_name
    if update.role is not None and update.role in ROLE_HIERARCHY:
        user.role = update.role
    if update.is_active is not None:
        user.is_active = update.is_active
    
    db.commit()
    db.refresh(user)
    log_action(db, current_user.id, "update_user", "user", user_id, 
               {"changes": update.model_dump(exclude_none=True)})
    return user
