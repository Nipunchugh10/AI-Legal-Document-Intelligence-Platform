from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import QARequest, QAResponse, QASourceItem
from app.agents.qa_agent import build_qa_graph, QAState

router = APIRouter()

@router.post(
    "/{contract_id}/ask",
    response_model=QAResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about a contract",
    description=(
        "Uses the Q&A Agent (Agent 5) to answer a natural language question about the contract. "
        "Answers are grounded in contract text chunks retrieved via RAG with citation sources."
    ),
)
async def ask_contract_question(
    contract_id: int,
    payload: QARequest,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A agent failed: {final_state['error']}",
        )

    # 3. Format sources into response schema
    sources = []
    for src in final_state.get("sources", []):
        sources.append(QASourceItem(
            chunk_index=src.get("chunk_index"),
            text=src.get("text"),
            similarity=src.get("similarity")
        ))

    return QAResponse(
        contract_id=contract_id,
        question=payload.question,
        answer=final_state.get("answer"),
        sources=sources
    )
