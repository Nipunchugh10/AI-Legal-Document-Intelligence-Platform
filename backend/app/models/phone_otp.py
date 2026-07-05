"""
Phone OTP Verification Model
-----------------------------
SQLAlchemy ORM definition for the `phone_otp_verifications` table.

Day 12 — Phone-Based Two-Factor Authentication: Backend Setup
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PhoneOTPVerification(Base):
    """Represents an active OTP verification request for a phone number."""

    __tablename__ = "phone_otp_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<PhoneOTPVerification phone={self.phone_number!r} verified={self.is_verified}>"
