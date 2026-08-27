"""
Contract Comparison API
-----------------------
Endpoint for comparing two versions of a contract, detecting added/removed/modified clauses,
calculating word-level diffs, and evaluating risk profile evolution.

Day 38 — Contract Comparison Feature — Backend
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService
from app.services.pdf_extractor import extract_document_text

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_contract_text(contract: Contract) -> str:
    """Helper to extract or retrieve full text of a contract."""
    if not os.path.exists(contract.upload_path):
        return ""
    try:
        extraction = extract_document_text(contract.upload_path)
        return extraction.get("text", "") if isinstance(extraction, dict) else ""
    except Exception as e:
        logger.warning("Failed to extract text for contract ID %d: %s", contract.id, e)
        return ""


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare two contracts",
    description=(
        "Performs clause-level semantic comparison, text-level character/word diffing, "
        "and risk profile delta evaluation between a baseline contract and a target/revised contract."
    ),
)
async def compare_contracts(
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compares two contracts owned by the current user.
    """
    # 1. Fetch and verify baseline contract
    base_contract = (
        db.query(Contract)
        .filter(Contract.id == payload.base_contract_id, Contract.user_id == current_user.id)
        .first()
    )
    if not base_contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline contract ID {payload.base_contract_id} not found or not owned by user.",
        )

    # 2. Fetch and verify target contract
    target_contract = (
        db.query(Contract)
        .filter(Contract.id == payload.target_contract_id, Contract.user_id == current_user.id)
        .first()
    )
    if not target_contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target contract ID {payload.target_contract_id} not found or not owned by user.",
        )

    # 3. Retrieve analysis records from database if available
    base_analysis_record = (
        db.query(Analysis).filter(Analysis.contract_id == base_contract.id).first()
    )
    base_analysis_json = (
        base_analysis_record.result_json if base_analysis_record and base_analysis_record.result_json else {}
    )

    target_analysis_record = (
        db.query(Analysis).filter(Analysis.contract_id == target_contract.id).first()
    )
    target_analysis_json = (
        target_analysis_record.result_json if target_analysis_record and target_analysis_record.result_json else {}
    )

    # 4. Extract raw document text
    base_text = _get_contract_text(base_contract)
    target_text = _get_contract_text(target_contract)

    # 5. Execute comparison algorithm via ComparisonService
    try:
        comparison_result = ComparisonService.perform_comparison(
            base_id=base_contract.id,
            base_filename=base_contract.filename,
            base_text=base_text,
            base_analysis=base_analysis_json,
            target_id=target_contract.id,
            target_filename=target_contract.filename,
            target_text=target_text,
            target_analysis=target_analysis_json,
        )
        return comparison_result
    except Exception as e:
        logger.error("Contract comparison execution failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute contract comparison: {str(e)}",
        )
