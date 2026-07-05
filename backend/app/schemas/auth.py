"""
Authentication Schemas
----------------------
Pydantic request/response models for the /auth endpoints.

Day 4 — Basic Authentication System
Day 12 — Phone-Based Two-Factor Authentication Schema Setup
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


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


class OTPRequest(BaseModel):
    """Body for requesting an OTP code to be sent to a phone number."""

    phone_number: str = Field(
        ...,
        description="Indian mobile number with +91 country code (e.g., +919876543210)",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        pattern = r"^\+91[6-9]\d{9}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid Indian mobile number. Must start with +91 followed by a 10-digit number starting with 6-9."
            )
        return v

    model_config = {"json_schema_extra": {"example": {"phone_number": "+919876543210"}}}


class OTPVerifyRequest(BaseModel):
    """Body for verifying an OTP code sent to a phone number."""

    phone_number: str = Field(
        ...,
        description="Indian mobile number with +91 country code (e.g., +919876543210)",
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP verification code",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        pattern = r"^\+91[6-9]\d{9}$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid Indian mobile number. Must start with +91 followed by a 10-digit number starting with 6-9."
            )
        return v

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP code must contain only numeric digits.")
        return v

    model_config = {"json_schema_extra": {"example": {"phone_number": "+919876543210", "otp_code": "123456"}}}


# ── Response Bodies ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned by POST /auth/login on success."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Returned by POST /auth/register and GET /auth/me."""

    id: int
    email: str
    is_active: bool
    phone_number: Optional[str]
    is_phone_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
