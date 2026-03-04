"""Authentication utilities."""

import os
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

_log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
_DEFAULT_SECRET = "dev_secret_key_change_in_prod"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)

if SECRET_KEY == _DEFAULT_SECRET:
    _log.warning(
        "⚠️  SECURITY WARNING: Using default SECRET_KEY. "
        "Set the SECRET_KEY environment variable for production!"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60   # Increased from 30

# Using pbkdf2_sha256 for better compatibility on Windows/different environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# ── Password policy ──────────────────────────────────────────────────────────
def validate_password(password: str) -> list[str]:
    """Validate password strength. Returns list of errors (empty = valid)."""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least 1 uppercase letter.")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain at least 1 digit.")
    return errors


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
