"""
Authentication Router
---------------------
Endpoints:
    POST /auth/register   — create a new user account
    POST /auth/login      — verify credentials, return JWT access token
    GET  /auth/me         — return current authenticated user info

Day 4 — Basic Authentication System

NOTE: This is a first-version auth system (access token only).
      Refresh tokens, server-side sessions, auto-logout, and SMS OTP 2FA
      are implemented in Phase 2A (Days 8–15).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


# ── POST /auth/register ────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Creates a new user account. The password is stored as a bcrypt hash — "
        "the plaintext is never persisted. Returns the created user (minus password)."
    ),
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user."""
    # Check email uniqueness
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create and persist the new user
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
    description=(
        "Verifies email and password. On success, returns a signed JWT access token "
        "valid for the duration configured in ACCESS_TOKEN_EXPIRE_MINUTES (.env)."
    ),
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and issue a JWT."""
    user = db.query(User).filter(User.email == body.email).first()

    # Use the same error message regardless of whether email or password is wrong
    # to prevent user enumeration via error message differences
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive",
        )

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token, token_type="bearer")


# ── GET /auth/me ───────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description=(
        "Returns the profile of the currently authenticated user. "
        "Requires a valid 'Authorization: Bearer <token>' header."
    ),
)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current user's profile."""
    return current_user
