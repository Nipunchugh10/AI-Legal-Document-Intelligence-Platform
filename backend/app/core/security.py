"""
Security Module (Stub)
----------------------
JWT encode/decode and password hashing utilities.
Full implementation happens on Day 4 (Basic Authentication System).
This stub is created on Day 2 so the module exists in the project structure.
"""

from passlib.context import CryptContext

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)
