
import os
from passlib.context import CryptContext

# Configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password."""
    # This matches the implementation in src/flagguard/auth/utils.py
    return pwd_context.hash(password)

if __name__ == "__main__":
    print("Testing password hashing...")
    try:
        pw = "admin123"
        print(f"Hashing password: '{pw}' (type: {type(pw)})")
        hashed = get_password_hash(pw)
        print(f"Success! Hash: {hashed[:20]}...")
    except Exception as e:
        print(f"FAILED with error: {e}")
        import traceback
        traceback.print_exc()
