"""
Account & Privacy Schemas
-------------------------
Pydantic models for data export, activity retention policy configuration,
and verified multi-step cascade account deletion.

Day 48 — History Privacy, Retention, and Data Export
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RetentionPolicyResponse(BaseModel):
    """Current user activity history retention policy."""

    data_retention_days: Optional[int] = Field(
        None,
        description="Number of days activity logs are retained. Null indicates indefinite retention."
    )
    message: str = Field(..., description="Status description of the retention policy.")


class RetentionPolicyUpdate(BaseModel):
    """Request payload to configure activity retention policy."""

    data_retention_days: Optional[int] = Field(
        None,
        description="Desired retention duration in days (e.g. 30, 90, 180, 365, or null for forever)."
    )

    @field_validator("data_retention_days")
    @classmethod
    def validate_retention_period(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (30, 90, 180, 365):
            raise ValueError("Retention period must be one of: 30, 90, 180, 365 days, or null (forever).")
        return v


class AccountDeleteOTPResponse(BaseModel):
    """Response returned when an account deletion confirmation OTP is dispatched."""

    message: str


class AccountDeleteRequest(BaseModel):
    """Request payload for permanent account and data deletion."""

    password: str = Field(..., min_length=1, description="Current account password for authentication verification.")
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit Email OTP confirmation code dispatched to the registered email."
    )

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP confirmation code must contain only numeric digits.")
        return v


class AccountDeleteResponse(BaseModel):
    """Response returned after successful cascade account deletion."""

    message: str
    deleted_contracts_count: int
    deleted_conversations_count: int
