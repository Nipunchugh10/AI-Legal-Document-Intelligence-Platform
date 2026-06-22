"""
Authentication Schemas
----------------------
Pydantic request/response models for the /auth endpoints.

Day 4 — Basic Authentication System
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


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


# ── Response Bodies ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned by POST /auth/login on success."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Returned by POST /auth/register and GET /auth/me."""

    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
