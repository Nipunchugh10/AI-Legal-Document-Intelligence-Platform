"""
Conversation Schemas
--------------------
Pydantic v2 validation models for Q&A conversation threads, messages,
and structured citation payloads.

Day 45 — History and Conversation Data Architecture
"""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConversationMessageBase(BaseModel):
    """Base schema for an individual message turn."""

    role: str = Field(..., description="'user' or 'assistant' (or 'system')")
    content: str = Field(..., min_length=1, description="Message text content")
    cited_clause_refs: Optional[Any] = Field(
        None, description="Optional structured citation coordinates and similarity metrics"
    )


class ConversationMessageCreate(ConversationMessageBase):
    """Schema for sending a new message into an active conversation."""
    pass


class ConversationMessageResponse(ConversationMessageBase):
    """Schema for returning a persisted message."""

    id: int
    conversation_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    """Base conversation attributes."""

    title: Optional[str] = Field("New Conversation", max_length=255)


class ConversationCreate(ConversationBase):
    """Schema for initializing a new conversation thread."""

    contract_id: int = Field(..., description="Target contract ID")
    initial_message: Optional[str] = Field(
        None, description="Optional starter question to submit immediately"
    )


class ConversationUpdate(BaseModel):
    """Schema for renaming or editing a conversation thread."""

    title: str = Field(..., min_length=1, max_length=255, description="Updated conversation title")


class ConversationResponse(ConversationBase):
    """Schema for returning conversation metadata in lists or summaries."""

    id: int
    user_id: int
    contract_id: int
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: Optional[int] = Field(0, description="Total messages in conversation")
    contract_filename: Optional[str] = Field(None, description="Associated contract filename")

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    """Full conversation history including ordered messages."""

    messages: List[ConversationMessageResponse] = Field(
        default_factory=list, description="Chronological message history"
    )

    model_config = ConfigDict(from_attributes=True)
