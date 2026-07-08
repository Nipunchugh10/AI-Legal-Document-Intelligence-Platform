"""
Authentication Schemas
----------------------
Pydantic request/response models for the /auth endpoints.

Day 14 (Refactored) — Email-Based Two-Factor Authentication Schema Setup
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request Bodies ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body for POST /auth/register"""

    email: EmailStr = Field(..., description="Valid email address for the new account")
    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
    )

    model_config = {"json_schema_extra": {"example": {"email": "user@example.com", "password": "secret123"}}}


class LoginRequest(BaseModel):
    """Body for POST /auth/login"""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")

    model_config = {"json_schema_extra": {"example": {"email": "user@example.com", "password": "secret123"}}}


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh"""

    refresh_token: str = Field(..., description="The refresh token issued at login")


class Email2FAConfirmRequest(BaseModel):
    """Body for verifying and enabling Email 2FA (POST /auth/2fa/confirm)"""

    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP verification code",
    )

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP code must contain only numeric digits.")
        return v

    model_config = {"json_schema_extra": {"example": {"otp_code": "123456"}}}


# ── Response Bodies ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned by POST /auth/login on success or when 2FA is required."""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    pending_2fa_token: Optional[str] = None
    message: Optional[str] = None


class LoginVerify2FARequest(BaseModel):
    """Body for verifying 2FA OTP at login."""

    pending_2fa_token: str = Field(..., description="Short-lived pending 2FA token from login response")
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP verification code",
    )

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP code must contain only numeric digits.")
        return v


class Resend2FAOTPRequest(BaseModel):
    """Body for resending 2FA OTP at login."""

    pending_2fa_token: str = Field(..., description="Short-lived pending 2FA token from login response")


class UserResponse(BaseModel):
    """Returned by POST /auth/register and GET /auth/me."""

    id: int
    email: str
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
