"""
Contract Model
--------------
SQLAlchemy ORM definition for the `contracts` table.

Each contract belongs to exactly one user and tracks the uploaded
PDF file path, processing status, and creation time.

Day 3 — Database Design and Migrations
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Contract(Base):
    """Represents an uploaded legal document (PDF)."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    upload_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Status lifecycle: pending → ingested → analyzed → failed
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships (back-populated when queried)
    user = relationship("User", backref="contracts")
    analyses = relationship(
        "Analysis", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} filename={self.filename!r} status={self.status!r}>"
