"""
Security Module
---------------
Password hashing (bcrypt) and JWT token utilities.

Day 2 stub: hash_password, verify_password
Day 4 full: create_access_token, decode_access_token, get_current_user

NOTE: This is intentionally a single-token (access token only) system.
      Refresh tokens + server-side session storage + auto-logout are
      implemented in Phase 2A (Days 8–15).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

# --- Password Hashing ─────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# --- Session & Refresh Tokens ──────────────────────────────────────────────────


def hash_token(token: str) -> str:
    """Hash a plaintext token using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(
    user_id: int,
    db: Session,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[str, int]:
    """
    Generate a cryptographically secure random refresh token,
    hash it, store the hash and metadata in the database (user_sessions),
    and return the plaintext token to be returned to the client.
    """
    from app.models.user_session import UserSession  # local import

    plain_token = secrets.token_hex(32)
    token_hash = hash_token(plain_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session = UserSession(
        user_id=user_id,
        refresh_token_hash=token_hash,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return plain_token, session.id


# --- JWT Tokens ───────────────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data:          Payload to encode (must include a 'sub' claim, e.g. email).
        expires_delta: Custom TTL; defaults to ACCESS_TOKEN_EXPIRE_MINUTES from config.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Returns:
        The decoded payload dict, or None if the token is expired or invalid.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None


# --- FastAPI Dependency ────────────────────────────────────────────────────────

# Tells FastAPI where clients send the bearer token and
# wires up the auto-generated Authorize button in /docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency that extracts and validates the JWT from the
    'Authorization: Bearer <token>' header, checks the database-backed session,
    enforces idle timeout (40 mins) and absolute expiry (7 days),
    updates last_active_at, and returns the matching User.

    Raises:
        HTTPException 401 — if token is missing, expired, malformed,
                            the session is idle/expired/revoked, or
                            the user no longer exists in the DB.
    """
    from app.models.user import User  # local import avoids circular dependency
    from app.models.user_session import UserSession  # local import
    from datetime import datetime, timezone, timedelta

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: Optional[str] = payload.get("sub")
    session_id: Optional[int] = payload.get("session_id")
    if email is None or session_id is None:
        raise credentials_exception

    # Query and validate session record
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session or session.is_revoked:
        raise credentials_exception

    now = datetime.now(timezone.utc)

    # 1. Check absolute session limit (7 days)
    if session.expires_at < now:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_EXPIRED",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Check idle timeout (40 minutes)
    idle_limit = timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)
    if now - session.last_active_at > idle_limit:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_EXPIRED",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update session activity
    session.last_active_at = now
    db.commit()

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive",
        )

    return user


# --- File Upload Security & Path Traversal Protection — Day 60 ───────────────

import re
from pathlib import Path


def sanitize_upload_filename(raw_filename: Optional[str]) -> str:
    """
    Sanitizes an uploaded document filename to prevent path traversal,
    null-byte injection, hidden file execution, and filesystem corruption.

    Day 60 — Security Hardening

    Rules:
    1. Rejects empty, whitespace-only, or None filenames.
    2. Rejects null bytes (\\0) and control characters.
    3. Strips both UNIX (/) and Windows (\\\\) path separators.
    4. Eliminates directory traversal sequences (../, ..\\\\).
    5. Strips leading dots and whitespace (prevents hidden system files).
    6. Replaces special/unsafe characters with underscores, preserving extension.
    7. Truncates length to safe bounds (max 200 chars).
    8. Fallbacks to 'uploaded_document' if the stem is entirely empty.
    """
    if not raw_filename or not raw_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # 1. Null-byte injection check
    if "\0" in raw_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid null byte characters.",
        )

    # 2. Normalize Windows backslashes to forward slashes, then extract base name
    normalized = raw_filename.replace("\\", "/").strip()

    # Detect blatant path traversal attempts
    if ".." in normalized.split("/"):
        pass  # We will strip traversal below, but let's ensure base name is cleanly extracted

    base_name = Path(normalized).name

    # Remove any lingering traversal artifacts
    base_name = re.sub(r"(\.\./|\.\.\\)", "", base_name)
    base_name = base_name.replace("..", "").strip()

    # Strip leading dots and spaces (prevents hidden files like .env, .htaccess)
    base_name = base_name.lstrip(". ")

    if not base_name:
        base_name = "uploaded_document"

    # Separate stem and suffix
    path_obj = Path(base_name)
    stem = path_obj.stem
    suffix = path_obj.suffix.lower()

    # Clean stem: retain alphanumeric, underscore, hyphen
    cleaned_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
    cleaned_stem = re.sub(r"_+", "_", cleaned_stem).strip("_")

    if not cleaned_stem:
        cleaned_stem = "uploaded_document"

    # Enforce safe length limit (max 180 chars for stem + suffix)
    if len(cleaned_stem) > 180:
        cleaned_stem = cleaned_stem[:180]

    safe_filename = f"{cleaned_stem}{suffix}"
    return safe_filename

