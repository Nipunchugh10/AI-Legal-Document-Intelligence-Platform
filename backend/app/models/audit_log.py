"""
AuditLog Model
--------------
SQLAlchemy ORM definition for the `audit_logs` table.

Records every significant user action with an immutable timestamp.
This table is append-only — rows are never updated or deleted,
preserving a complete, honest history for security and compliance.

Formal event taxonomy defined in `app.core.audit_events.AuditEventType`:
  - Authentication: USER_REGISTERED, USER_LOGIN, TWO_FACTOR_*, etc.
  - Contracts: CONTRACT_UPLOADED, CONTRACT_PROCESSED, CONTRACT_VIEWED, etc.
  - Intelligence: ANALYSIS_QUEUED, ANALYSIS_STARTED, ANALYSIS_COMPLETED, etc.
  - Interactive: QA_MESSAGE_SENT, SEARCH_PERFORMED, COMPARISON_RUN, etc.
  - Governance: DATA_EXPORTED, ACCOUNT_DELETED

Day 3 — Database Design and Migrations
Day 45 — Extended with client telemetry (ip_address, user_agent, status) and composite indexing.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AuditLog(Base):
    """Immutable record of a user action or system operation."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # nullable=True with ON DELETE SET NULL: preserved even if user account is deleted
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # ID of the primary resource this action affected (e.g., contract_id, conversation_id)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Execution status: "SUCCESS", "FAILURE", "WARNING"
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    # Client network context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Flexible JSON bag for extra context (filename, latency_ms, filters, error, etc.)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} user_id={self.user_id} "
            f"action={self.action!r} status={self.status!r} ts={self.timestamp}>"
        )
