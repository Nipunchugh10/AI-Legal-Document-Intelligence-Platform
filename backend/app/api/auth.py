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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
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
    RefreshRequest,
    OTPRequest,
    OTPVerifyRequest,
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
    summary="Log in and receive access & refresh tokens",
    description=(
        "Verifies email and password. On success, returns a signed JWT access token "
        "and a secure database-backed refresh token."
    ),
)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user, establish a session, and issue access & refresh tokens."""
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

    # Extract client IP and user-agent for session tracking
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")

    refresh_token, session_id = create_refresh_token(
        user_id=user.id,
        db=db,
        device_info=device_info,
        ip_address=ip_address,
    )
    access_token = create_access_token(data={"sub": user.email, "session_id": session_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


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


# ── POST /auth/refresh ─────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a new access token and a rotated refresh token.",
)
def refresh(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange refresh token for a new access token and rotated refresh token."""
    from datetime import datetime, timezone
    from app.models.user_session import UserSession
    from app.core.security import hash_token

    token_hash = hash_token(body.refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()

    if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old refresh token (rotation)
    session.is_revoked = True
    session.last_active_at = datetime.now(timezone.utc)
    db.commit()

    # Issue new access + refresh tokens
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")

    new_refresh_token, new_session_id = create_refresh_token(
        user_id=session.user_id,
        db=db,
        device_info=device_info,
        ip_address=ip_address,
    )
    access_token = create_access_token(data={"sub": session.user.email, "session_id": new_session_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


# ── POST /auth/logout ──────────────────────────────────────────────────────────

@router.post(
    "/logout",
    summary="Log out of the current session",
    description="Revokes the refresh token associated with the session.",
)
def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Revoke the current session's refresh token."""
    from app.models.user_session import UserSession
    from app.core.security import hash_token

    token_hash = hash_token(body.refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()

    if session:
        session.is_revoked = True
        db.commit()

    return {"status": "success", "message": "Successfully logged out"}


# ── POST /auth/2fa/add-phone ──────────────────────────────────────────────────

@router.post(
    "/2fa/add-phone",
    summary="Add a phone number for 2FA setup",
    description="Registers an Indian phone number for the authenticated user and triggers sending an OTP code.",
)
def add_phone(
    body: OTPRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.otp_service import send_otp
    from app.services.phone_validator import validate_indian_phone

    normalized_phone = validate_indian_phone(body.phone_number)

    # Check if this phone number is already registered by another verified user
    other_user = db.query(User).filter(
        User.phone_number == normalized_phone,
        User.is_phone_verified == True,
        User.id != current_user.id
    ).first()
    if other_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered by another account.",
        )

    # Save phone number to current user (even if not verified yet)
    current_user.phone_number = normalized_phone
    current_user.is_phone_verified = False
    db.commit()

    # Trigger sending OTP
    send_otp(db, normalized_phone)

    return {
        "status": "success",
        "message": "Verification OTP sent to your phone number.",
        "phone_number": normalized_phone
    }


# ── POST /auth/2fa/confirm-phone ──────────────────────────────────────────────

@router.post(
    "/2fa/confirm-phone",
    summary="Confirm phone number with OTP",
    description="Verifies the OTP code submitted by the user to activate 2FA.",
)
def confirm_phone(
    body: OTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.otp_service import verify_otp
    from app.services.phone_validator import validate_indian_phone

    normalized_phone = validate_indian_phone(body.phone_number)

    # Ensure the user is verifying their own registered phone number
    if current_user.phone_number != normalized_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted phone number does not match your registered phone number. Please run add-phone first.",
        )

    # Verify OTP code
    verify_otp(db, normalized_phone, body.otp_code)

    # Mark user phone as verified
    current_user.is_phone_verified = True
    db.commit()

    return {
        "status": "success",
        "message": "Phone number successfully verified. Two-factor authentication (2FA) is now active."
    }


