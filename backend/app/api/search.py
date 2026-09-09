"""
Search API Router
-----------------
FastAPI endpoint for Day 40 Semantic Search across contracts.
Enforces multi-tenant data isolation, executes vector similarity search via SearchService,
and returns ranked contract matches with cited excerpts and metadata.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.audit_events import AuditEventType
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.search import SemanticSearchResponse
from app.services.audit_logger import log_activity
from app.services.search_service import SearchService

router = APIRouter()


@router.get(
    "/search",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Search Across User Contracts",
    description=(
        "Performs cosine similarity vector search across all indexed contract text chunks "
        "belonging to the authenticated user. Supports metadata filtering by document type, "
        "risk level, date range, and minimum similarity threshold."
    ),
)
async def search_contracts(
    request: Request,
    q: str = Query(..., min_length=1, description="Semantic search query string"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of contracts to return"),
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g., NDA, Employment, Lease)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk tier (CRITICAL, HIGH, MEDIUM, LOW, SAFE)"),
    date_from: Optional[datetime] = Query(None, description="Filter contracts created on or after UTC datetime"),
    date_to: Optional[datetime] = Query(None, description="Filter contracts created on or before UTC datetime"),
    contract_id: Optional[int] = Query(None, description="Optionally restrict search to a specific contract ID"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search all contracts owned by the authenticated user using vector embeddings.
    """
    results = SearchService.search_user_contracts(
        db=db,
        user_id=current_user.id,
        query=q,
        limit=limit,
        document_type=document_type,
        risk_level=risk_level,
        date_from=date_from,
        date_to=date_to,
        contract_id=contract_id,
        min_similarity=min_similarity,
    )

    log_activity(
        db=db,
        action=AuditEventType.SEARCH_PERFORMED.value,
        user_id=current_user.id,
        metadata={
            "query": q,
            "total_contracts_matched": results.total_contracts_matched,
            "total_chunks_matched": results.total_chunks_matched,
        },
        request=request,
    )

    return results

