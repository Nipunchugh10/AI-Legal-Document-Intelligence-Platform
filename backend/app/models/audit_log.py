"""
AuditLog Model
--------------
SQLAlchemy ORM definition for the `audit_logs` table.

Records every significant user action with a timestamp.
This table is append-only — rows are never updated or deleted,
preserving a complete, honest history for security and compliance.

Common action values:
  user.registered     — new account created
  user.login          — successful login
  user.login_failed   — failed login attempt
  user.logout         — explicit logout
  user.2fa_enabled    — phone 2FA activated (Phase 2A)
  contract.uploaded   — PDF uploaded
  contract.analyzed   — analysis pipeline completed
  contract.deleted    — document removed

Day 3 — Database Design and Migrations
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AuditLog(Base):
    """Immutable record of a user action."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # nullable=True: some actions may be system-level with no associated user
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # ID of the primary resource this action affected (e.g., contract_id)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Flexible JSON bag for extra context (IP address, error message, etc.)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} user_id={self.user_id} "
            f"action={self.action!r} ts={self.timestamp}>"
        )
