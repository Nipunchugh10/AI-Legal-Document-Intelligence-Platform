"""
Authentication Router
---------------------
Endpoints:
    POST /auth/register     — create a new user account
    POST /auth/login        — verify credentials, return JWT access token or trigger 2FA
    GET  /auth/me           — return current authenticated user info
    POST /auth/refresh      — refresh expired access token
    POST /auth/logout       — log out and revoke session
    POST /auth/2fa/enable   — trigger OTP sending to enable Email 2FA
    POST /auth/2fa/confirm  — confirm OTP code to activate Email 2FA
    POST /auth/2fa/disable  — disable Email 2FA for the account
    POST /auth/2fa/login-verify  — verify 2FA OTP at login
    POST /auth/2fa/resend-otp    — resend 2FA OTP with 30-second cooldown
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone

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
    Email2FAConfirmRequest,
    LoginVerify2FARequest,
    Resend2FAOTPRequest,
    GoogleLoginRequest,
)

router = APIRouter()


def mask_email(email: str) -> str:
    """Mask email for privacy, e.g. nipunchugh553@gmail.com -> n••••3@gmail.com"""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    name, domain = parts
    if len(name) <= 2:
        return name[0] + "••••" + "@" + domain
    return name[0] + "••••" + name[-1] + "@" + domain


# ── POST /auth/register ────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Creates a new user account. The password is stored as a bcrypt hash — "
        "the plaintext is never persisted. Returns the created user."
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
        is_2fa_enabled=False,
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
        "and a secure database-backed refresh token. If Email 2FA is enabled, triggers OTP and returns a pending token."
    ),
)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user, establish a session, and issue access & refresh tokens or trigger 2FA."""
    from app.services.otp_service import send_otp

    user = db.query(User).filter(User.email == body.email).first()

    # Generic error message to prevent account enumeration
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

    # Check if user has Email 2FA enabled
    if user.is_2fa_enabled:
        # Trigger OTP sending to registered email
        send_otp(db, user.email)

        # Generate a short-lived pending 2FA token (expires in 5 minutes)
        pending_2fa_token = create_access_token(
            data={"sub": user.email, "pending_2fa": True},
            expires_delta=timedelta(minutes=5)
        )

        return TokenResponse(
            requires_2fa=True,
            pending_2fa_token=pending_2fa_token,
            message=f"Code sent to {mask_email(user.email)}"
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
    description="Returns the profile of the currently authenticated user.",
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


# ── POST /auth/2fa/enable ──────────────────────────────────────────────────────

@router.post(
    "/2fa/enable",
    summary="Trigger Email 2FA setup",
    description="Generates and dispatches a 6-digit verification code to the authenticated user's email address.",
)
def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.otp_service import send_otp

    # Trigger sending OTP to user's registered email
    send_otp(db, current_user.email)

    return {
        "status": "success",
        "message": f"Verification OTP sent to your registered email address: {mask_email(current_user.email)}",
        "email": mask_email(current_user.email)
    }


# ── POST /auth/2fa/confirm ─────────────────────────────────────────────────────

@router.post(
    "/2fa/confirm",
    summary="Confirm OTP and enable Email 2FA",
    description="Verifies the OTP code submitted by the user. On success, activates Email 2FA on the account.",
)
def confirm_2fa(
    body: Email2FAConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.otp_service import verify_otp

    # Verify OTP code against registered email
    verify_otp(db, current_user.email, body.otp_code)

    # Activate 2FA on the account
    current_user.is_2fa_enabled = True
    db.commit()

    return {
        "status": "success",
        "message": "Two-factor authentication (2FA) is now active on your account."
    }


# ── POST /auth/2fa/disable ─────────────────────────────────────────────────────

@router.post(
    "/2fa/disable",
    summary="Disable Email 2FA",
    description="Disables Email 2FA on the authenticated user's account.",
)
def disable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.is_2fa_enabled = False
    db.commit()

    return {
        "status": "success",
        "message": "Two-factor authentication (2FA) has been disabled on your account."
    }


# ── POST /auth/2fa/login-verify ───────────────────────────────────────────────

@router.post(
    "/2fa/login-verify",
    response_model=TokenResponse,
    summary="Verify 2FA OTP at login",
    description="Accepts a pending 2FA token and 6-digit OTP code. If valid, establishes session and returns access + refresh tokens.",
)
def login_verify_2fa(
    body: LoginVerify2FARequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    from app.core.security import decode_access_token
    from app.services.otp_service import verify_otp

    # 1. Decode and validate the pending 2FA token
    payload = decode_access_token(body.pending_2fa_token)
    if not payload or not payload.get("pending_2fa"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    # 2. Query user and check status
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not active on this account.",
        )

    # 3. Verify OTP
    verify_otp(db, user.email, body.otp_code)

    # 4. Success! Issue real session and tokens
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


# ── POST /auth/2fa/resend-otp ─────────────────────────────────────────────────

@router.post(
    "/2fa/resend-otp",
    summary="Resend 2FA OTP at login",
    description="Resends the verification OTP code for a user in the pending 2FA state, with a 30-second cooldown.",
)
def resend_2fa_otp(
    body: Resend2FAOTPRequest,
    db: Session = Depends(get_db),
):
    from app.core.security import decode_access_token
    from app.services.otp_service import send_otp
    from app.models.email_otp import EmailOTPVerification

    # 1. Decode and validate the pending 2FA token
    payload = decode_access_token(body.pending_2fa_token)
    if not payload or not payload.get("pending_2fa"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    # 2. Query user and check status
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please log in again.",
        )

    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not active on this account.",
        )

    # 3. Cooldown check (30 seconds)
    otp_entry = db.query(EmailOTPVerification).filter(
        EmailOTPVerification.email == user.email
    ).first()
    if otp_entry:
        now = datetime.now(timezone.utc)
        time_elapsed = now - otp_entry.created_at
        if time_elapsed < timedelta(seconds=30):
            seconds_left = int(30 - time_elapsed.total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {seconds_left} seconds before requesting a new OTP.",
            )

    # 4. Trigger sending OTP
    send_otp(db, user.email)

    return {
        "status": "success",
        "message": f"Code sent to {mask_email(user.email)}"
    }


# ── POST /auth/google-login ────────────────────────────────────────────────────

@router.post(
    "/google-login",
    response_model=TokenResponse,
    summary="Sign in or register with Google OAuth credentials",
    description=(
        "Verifies the Google OAuth ID Token (credential). If the user is new, automatically "
        "registers them. Returns active access and refresh tokens. Bypasses 2FA checks entirely."
    ),
)
def google_login(
    body: GoogleLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user using Google OAuth ID Token."""
    import secrets
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from app.core.config import get_settings

    settings = get_settings()

    # 1. Verify Google Credential Token
    try:
        id_info = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Extract user information
    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account does not provide an email address",
        )

    # Normalize email
    email_normalized = email.strip().lower()

    # 3. Check if user exists or register automatically
    user = db.query(User).filter(User.email == email_normalized).first()
    if not user:
        # Create and persist a new user with random password
        user = User(
            email=email_normalized,
            hashed_password=hash_password(secrets.token_hex(16)),
            is_active=True,
            is_2fa_enabled=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is inactive",
            )

    # 4. Success! Issue active session credentials directly, bypassing 2FA OTP prompt completely
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
        requires_2fa=False,
    )
