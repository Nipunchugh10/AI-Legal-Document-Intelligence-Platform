"""
Analysis Model
--------------
SQLAlchemy ORM definition for the `analyses` table.

Each row stores the JSON output of one analysis step for a contract.
The `analysis_type` field identifies which agent produced the result:
  raw_text        — plain-text extracted from PDF (Day 16)
  chunks          — preprocessed text chunks (Day 17)
  parsed          — document type / parties (Agent 1, Day 21)
  clauses         — extracted clause list (Agent 2, Day 22)
  risks           — identified risk flags (Agent 3, Day 23)
  compliance      — compliance check results (Agent 4, Day 25)
  summary         — executive summary (Agent 5, Day 26)

Day 3 — Database Design and Migrations
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class Analysis(Base):
    """Stores the JSON result of one analysis operation on a contract."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contract_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    contract = relationship("Contract", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} contract_id={self.contract_id} type={self.analysis_type!r}>"
