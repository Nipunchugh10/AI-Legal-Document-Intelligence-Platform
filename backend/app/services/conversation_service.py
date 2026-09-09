"""
Conversation Service
--------------------
Handles stateful Q&A conversation thread lifecycle, message persistence,
structured legal citations tracking, and retrieval.

Day 46 — Activity History Backend
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ConversationMessage
from app.models.contract import Contract
from app.schemas.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationMessageResponse,
)

logger = logging.getLogger(__name__)


def generate_conversation_title(question: str) -> str:
    """Derives a concise, professional conversation title from the initial question."""
    clean = question.strip().replace("\n", " ")
    if len(clean) <= 60:
        return clean
    return clean[:57].rstrip() + "..."


def get_or_create_conversation(
    db: Session,
    user_id: int,
    contract_id: int,
    title: Optional[str] = None,
    conversation_id: Optional[int] = None,
) -> Conversation:
    """
    Retrieves an existing conversation thread by ID (verifying ownership),
    or returns the most recent active thread for the contract,
    or initializes a brand-new conversation.
    """
    # 1. Direct fetch if ID provided
    if conversation_id:
        convo = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.contract_id == contract_id,
            )
            .first()
        )
        if convo:
            return convo

    # 2. Check for most recent active conversation for this contract
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.contract_id == contract_id,
        )
        .order_by(desc(Conversation.last_message_at))
        .first()
    )
    if convo:
        return convo

    # 3. Create a fresh conversation
    default_title = title or "New Conversation"
    new_convo = Conversation(
        user_id=user_id,
        contract_id=contract_id,
        title=default_title,
        created_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )
    db.add(new_convo)
    db.commit()
    db.refresh(new_convo)
    return new_convo


def save_conversation_turn(
    db: Session,
    conversation: Conversation,
    question: str,
    answer: str,
    sources: Optional[List[Any]] = None,
) -> Tuple[ConversationMessage, ConversationMessage]:
    """
    Appends a user question and assistant answer pair to the conversation,
    preserving cited clause snippets and updating the conversation's recency timestamp.
    Auto-generates a descriptive title if still set to the default.
    """
    now = datetime.now(timezone.utc)

    # 1. User Message
    user_msg = ConversationMessage(
        conversation_id=conversation.id,
        role="user",
        content=question,
        created_at=now,
    )
    db.add(user_msg)

    # 2. Assistant Message with citations
    assistant_msg = ConversationMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        cited_clause_refs=sources,
        created_at=now,
    )
    db.add(assistant_msg)

    # 3. Update Conversation recency & title if default
    conversation.last_message_at = now
    if conversation.title in ("New Conversation", "New Chat", None, ""):
        conversation.title = generate_conversation_title(question)

    db.commit()
    db.refresh(conversation)
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return user_msg, assistant_msg


def list_user_conversations(
    db: Session,
    user_id: int,
    contract_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ConversationResponse]:
    """
    Lists conversation summaries for a user, sorted most recent first.
    Includes message counts and associated contract filenames.
    """
    query = (
        db.query(
            Conversation,
            Contract.filename.label("contract_filename"),
            func.count(ConversationMessage.id).label("message_count"),
        )
        .join(Contract, Conversation.contract_id == Contract.id)
        .outerjoin(ConversationMessage, Conversation.id == ConversationMessage.conversation_id)
        .filter(Conversation.user_id == user_id)
    )

    if contract_id:
        query = query.filter(Conversation.contract_id == contract_id)

    query = (
        query.group_by(Conversation.id, Contract.filename)
        .order_by(desc(Conversation.last_message_at))
        .offset(offset)
        .limit(limit)
    )

    results = []
    for convo, filename, count in query.all():
        results.append(
            ConversationResponse(
                id=convo.id,
                user_id=convo.user_id,
                contract_id=convo.contract_id,
                title=convo.title,
                created_at=convo.created_at,
                last_message_at=convo.last_message_at,
                message_count=count or 0,
                contract_filename=filename,
            )
        )
    return results


def get_conversation_detail(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> Optional[ConversationDetailResponse]:
    """
    Fetches full chronological message transcript for a specific conversation.
    Verifies user ownership.
    """
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    if not convo:
        return None

    # Contract filename lookup
    contract = db.query(Contract).filter(Contract.id == convo.contract_id).first()
    contract_filename = contract.filename if contract else None

    # Ordered messages
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )

    msg_responses = [
        ConversationMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            cited_clause_refs=m.cited_clause_refs,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return ConversationDetailResponse(
        id=convo.id,
        user_id=convo.user_id,
        contract_id=convo.contract_id,
        title=convo.title,
        created_at=convo.created_at,
        last_message_at=convo.last_message_at,
        message_count=len(msg_responses),
        contract_filename=contract_filename,
        messages=msg_responses,
    )


def update_conversation_title(
    db: Session,
    user_id: int,
    conversation_id: int,
    new_title: str,
) -> Optional[Conversation]:
    """Updates a conversation title."""
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    if not convo:
        return None

    convo.title = new_title.strip()[:255]
    db.commit()
    db.refresh(convo)
    return convo


def delete_conversation(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> bool:
    """Deletes a conversation thread and cascades message deletion."""
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    if not convo:
        return False

    db.delete(convo)
    db.commit()
    return True
