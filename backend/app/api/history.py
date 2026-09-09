"""
History and Conversations Router
--------------------------------
API endpoints for user activity timeline telemetry and stateful Q&A conversation threads.

Day 46 — Activity History Backend
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.audit_log import AuditLogFeedResponse, AuditLogResponse
from app.schemas.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationUpdate,
)
from app.services.audit_logger import get_user_activity
from app.services.conversation_service import (
    list_user_conversations,
    get_conversation_detail,
    update_conversation_title,
    delete_conversation,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Activity History Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=AuditLogFeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user activity history feed",
    description=(
        "Retrieves a paginated, filterable timeline of user actions (logins, uploads, "
        "analyses, searches, and Q&A conversations) enriched with categories and plain English descriptions."
    ),
)
async def get_activity_history(
    category: Optional[str] = Query(None, description="Category filter (AUTH, CONTRACTS, ANALYSIS, CHAT, SEARCH, SECURITY)"),
    action: Optional[str] = Query(None, description="Specific AuditEventType action filter"),
    event_status: Optional[str] = Query(None, alias="status", description="Status filter (SUCCESS, FAILURE)"),
    start_date: Optional[datetime] = Query(None, description="ISO timestamp filter (start)"),
    end_date: Optional[datetime] = Query(None, description="ISO timestamp filter (end)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_user_activity(
        db=db,
        user_id=current_user.id,
        category=category,
        action=action,
        status=event_status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return AuditLogFeedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Conversation History Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List past Q&A conversations",
    description="Retrieves all past Q&A conversation threads for the authenticated user, sorted most recent first.",
)
async def list_conversations(
    contract_id: Optional[int] = Query(None, description="Optional contract ID filter"),
    limit: int = Query(50, ge=1, le=200, description="Max threads to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_user_conversations(
        db=db,
        user_id=current_user.id,
        contract_id=contract_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail with messages",
    description="Retrieves the complete message history and source citations for a specific conversation thread.",
)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo_detail = get_conversation_detail(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    if not convo_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by user.",
        )
    return convo_detail


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update conversation title",
    description="Renames an existing conversation thread.",
)
async def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = update_conversation_title(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        new_title=payload.title,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by user.",
        )

    return ConversationResponse(
        id=updated.id,
        user_id=updated.user_id,
        contract_id=updated.contract_id,
        title=updated.title,
        created_at=updated.created_at,
        last_message_at=updated.last_message_at,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete conversation thread",
    description="Deletes a conversation thread and cascade-deletes all associated messages.",
)
async def remove_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = delete_conversation(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by user.",
        )
    return {"message": "Conversation deleted successfully", "id": conversation_id}
