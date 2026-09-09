"""
Conversation & ConversationMessage Models
-----------------------------------------
SQLAlchemy ORM definitions for user-facing interactive contract Q&A conversations.

Distinct from append-only security `audit_logs`, conversations represent
stateful, user-browsable dialogue threads that can be revisited, renamed,
resumed, and deleted.

Day 45 — History and Conversation Data Architecture
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class Conversation(Base):
    """
    Represents a persistent Q&A conversation thread anchored to a specific contract
    and owned by a user.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Title auto-generated from first question snippet or user-customized
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # Updated on each new message for chronological sorting
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="conversations")
    contract = relationship("Contract", back_populates="conversations")
    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_conversations_user_last_message", "user_id", "last_message_at"),
        Index("ix_conversations_contract_last_message", "contract_id", "last_message_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} user_id={self.user_id} "
            f"contract_id={self.contract_id} title={self.title!r}>"
        )


class ConversationMessage(Base):
    """
    Individual turn within a conversation (user question or assistant legal answer),
    preserving verbatim cited clauses and source coordinates in `cited_clause_refs`.
    """

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Role: 'user' or 'assistant'
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Full textual message payload
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured citations: list of {clause_id, page, section, text, similarity, ...}
    cited_clause_refs: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationship back to parent conversation
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_conversation_messages_convo_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMessage id={self.id} convo_id={self.conversation_id} "
            f"role={self.role!r} ts={self.created_at}>"
        )
