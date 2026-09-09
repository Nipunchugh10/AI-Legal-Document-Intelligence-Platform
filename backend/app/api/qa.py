"""
Contract Q&A Router
-------------------
API endpoints for grounded conversational Q&A over contract text.

Day 26 — Q&A Agent Endpoint
Day 46 — Conversation persistence, message citation history, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.audit_events import AuditEventType
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import QARequest, QAResponse, QASourceItem
from app.agents.qa_agent import build_qa_graph, QAState
from app.services.audit_logger import log_activity
from app.services.conversation_service import (
    get_or_create_conversation,
    save_conversation_turn,
)

router = APIRouter()


@router.post(
    "/{contract_id}/ask",
    response_model=QAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about a contract",
    description=(
        "Uses the Q&A Agent (Agent 5) to answer a natural language question about the contract. "
        "Answers are grounded in contract text chunks retrieved via RAG with citation sources, "
        "and dialogue turns are automatically persisted to the conversation history."
    ),
)
async def ask_contract_question(
    contract_id: int,
    payload: QARequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Fetch contract & verify ownership
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.user_id == current_user.id)
        .first()
    )
    if not contract:
        log_activity(
            db=db,
            action=AuditEventType.QA_MESSAGE_SENT.value,
            user_id=current_user.id,
            resource_id=contract_id,
            status="FAILURE",
            metadata={"error": "Contract not found or not owned", "contract_id": contract_id},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found or not owned by user.",
        )

    # 2. Invoke the Q&A Agent graph
    initial_state: QAState = {
        "contract_id": contract_id,
        "question": payload.question,
        "answer": "",
        "sources": [],
        "error": None,
    }

    qa_graph = build_qa_graph()
    final_state = qa_graph.invoke(initial_state)

    if final_state.get("error"):
        log_activity(
            db=db,
            action=AuditEventType.QA_MESSAGE_SENT.value,
            user_id=current_user.id,
            resource_id=contract_id,
            status="FAILURE",
            metadata={
                "error": str(final_state["error"]),
                "filename": contract.filename,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A agent failed: {final_state['error']}",
        )

    # 3. Format sources into response schema
    sources = []
    sources_raw = []
    for src in final_state.get("sources", []):
        item = QASourceItem(
            chunk_index=src.get("chunk_index"),
            text=src.get("text"),
            similarity=src.get("similarity"),
        )
        sources.append(item)
        sources_raw.append({
            "chunk_index": src.get("chunk_index"),
            "text": src.get("text"),
            "similarity": src.get("similarity"),
        })

    # 4. Day 46: Persist conversation thread and messages
    convo = get_or_create_conversation(
        db=db,
        user_id=current_user.id,
        contract_id=contract_id,
        conversation_id=payload.conversation_id,
    )

    save_conversation_turn(
        db=db,
        conversation=convo,
        question=payload.question,
        answer=final_state.get("answer") or "",
        sources=sources_raw,
    )

    # 5. Record audit activity
    log_activity(
        db=db,
        action=AuditEventType.QA_MESSAGE_SENT.value,
        user_id=current_user.id,
        resource_id=contract_id,
        status="SUCCESS",
        metadata={
            "conversation_id": convo.id,
            "filename": contract.filename,
            "question_preview": payload.question[:60],
            "sources_count": len(sources),
        },
        request=request,
    )

    return QAResponse(
        contract_id=contract_id,
        conversation_id=convo.id,
        question=payload.question,
        answer=final_state.get("answer"),
        sources=sources,
    )
