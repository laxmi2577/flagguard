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
        # Log failed login attempt for security auditing
        _failed_user_id = user.id if user else None
        try:
            failed_log = AuditLog(
                user_id=_failed_user_id,
                action="login_failed",
                resource_type="auth",
                resource_id=form_data.username,
                details={"reason": "invalid_credentials"}
            )
            db.add(failed_log)
            db.commit()
        except Exception:
            pass  # Don't let audit logging failure prevent error response
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        # Log disabled account login attempt
        try:
            disabled_log = AuditLog(
                user_id=user.id,
                action="login_failed",
                resource_type="auth",
                resource_id=user.email,
                details={"reason": "account_disabled"}
            )
            db.add(disabled_log)
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact admin.",
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


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Deactivate a user (admin only). Does not delete permanently."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    db.commit()
    log_action(db, current_user.id, "deactivate_user", "user", user_id)
    return {"status": "deactivated"}


# --- Signup Request & Approval ---

class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    requested_role: str = "viewer"  # viewer or analyst
    reason: str = ""

class PendingUserOut(BaseModel):
    id: str
    full_name: str
    email: str
    requested_role: str
    reason: str
    status: str
    requested_at: str | None

    class Config:
        from_attributes = True


@router.post("/signup-request")
def signup_request(req: SignupRequest, db: Session = Depends(get_db)):
    """Submit a signup request (no auth needed). Admin must approve before login."""
    from flagguard.core.models.tables import PendingUser
    
    # Check not already in users
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already has an active account")
    # Check not already pending
    existing = db.query(PendingUser).filter(PendingUser.email == req.email).first()
    if existing and existing.status == "pending":
        raise HTTPException(status_code=400, detail="A pending request already exists for this email")
    
    if req.requested_role not in ("viewer", "analyst"):
        raise HTTPException(status_code=400, detail="Role must be 'viewer' or 'analyst'")
    
    hashed = get_password_hash(req.password)
    pending = PendingUser(
        full_name=req.full_name,
        email=req.email,
        hashed_password=hashed,
        requested_role=req.requested_role,
        reason=req.reason,
    )
    db.add(pending)
    db.commit()
    return {"status": "pending", "message": "Your request has been submitted. An admin will review it shortly."}


@router.get("/pending", response_model=list[PendingUserOut])
def list_pending(
    status_filter: str | None = None,
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """List all pending signup requests (admin only)."""
    from flagguard.core.models.tables import PendingUser
    q = db.query(PendingUser)
    if status_filter:
        q = q.filter(PendingUser.status == status_filter)
    else:
        q = q.filter(PendingUser.status == "pending")
    return q.order_by(PendingUser.requested_at.desc()).all()


@router.post("/approve/{pending_id}", response_model=UserOut)
def approve_signup(
    pending_id: str,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Approve a signup request — creates User and sends notification (admin only)."""
    from flagguard.core.models.tables import PendingUser, Notification
    from datetime import datetime as dt
    
    pending = db.query(PendingUser).filter(PendingUser.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Pending request not found")
    if pending.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {pending.status}")
    
    # Create the actual user
    new_user = User(
        email=pending.email,
        hashed_password=pending.hashed_password,
        full_name=pending.full_name,
        role=pending.requested_role,
        is_active=True,
    )
    db.add(new_user)
    
    # Update pending record
    pending.status = "approved"
    pending.reviewed_at = dt.utcnow()
    pending.reviewed_by = current_user.id
    
    db.commit()
    db.refresh(new_user)
    
    # Create notification for the new user
    notif = Notification(
        user_id=new_user.id,
        title="Access Approved",
        message=f"Your request for {pending.requested_role} access has been approved! You can now sign in.",
        type="success",
    )
    db.add(notif)
    db.commit()
    
    log_action(db, current_user.id, "approve_signup", "user", new_user.id, {"email": new_user.email})
    return new_user


@router.post("/reject/{pending_id}")
def reject_signup(
    pending_id: str,
    reason: str = "Request denied by admin.",
    current_user: Annotated[User, Depends(require_role("admin"))] = None,
    db: Session = Depends(get_db)
):
    """Reject a signup request (admin only)."""
    from flagguard.core.models.tables import PendingUser
    from datetime import datetime as dt
    
    pending = db.query(PendingUser).filter(PendingUser.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Pending request not found")
    if pending.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {pending.status}")
    
    pending.status = "rejected"
    pending.reviewed_at = dt.utcnow()
    pending.reviewed_by = current_user.id
    pending.reason = reason  # store rejection reason
    db.commit()
    
    log_action(db, current_user.id, "reject_signup", "pending_user", pending_id)
    return {"status": "rejected"}


# --- Notifications ---

@router.get("/notifications")
def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    unread_only: bool = False
):
    """Get notifications for the current user."""
    from flagguard.core.models.tables import Notification
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    notifs = q.order_by(Notification.created_at.desc()).limit(50).all()
    return [
        {"id": n.id, "title": n.title, "message": n.message,
         "type": n.type, "is_read": n.is_read, "created_at": str(n.created_at)}
        for n in notifs
    ]


@router.post("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    from flagguard.core.models.tables import Notification
    n = db.query(Notification).filter(
        Notification.id == notif_id, Notification.user_id == current_user.id
    ).first()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "ok"}


# --- Password Reset (admin resets any user) ---

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class AdminPasswordReset(BaseModel):
    new_password: str

@router.post("/change-password")
def change_password(
    body: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Change own password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    log_action(db, current_user.id, "change_password", "user", current_user.id)
    return {"status": "password changed"}


@router.post("/reset-password/{user_id}")
def admin_reset_password(
    user_id: str,
    body: AdminPasswordReset,
    current_user: Annotated[User, Depends(require_role("admin"))],
    db: Session = Depends(get_db)
):
    """Admin resets any user's password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    log_action(db, current_user.id, "reset_password", "user", user_id)
    return {"status": "password reset"}

