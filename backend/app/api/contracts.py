"""
Contracts Router
----------------
Endpoints:
    POST /contracts/upload   — upload a PDF contract, save to disk, record in DB
    GET  /contracts/          — list all contracts for the current user
    GET  /contracts/{id}      — retrieve details of a specific contract

Day 5 — File Upload System
"""

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import ContractResponse, TextExtractionResponse

router = APIRouter()
settings = get_settings()


# ── POST /contracts/upload ───────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF contract",
    description=(
        "Uploads a PDF contract (max 10MB). The file is stored locally in the "
        "configured uploads directory, and metadata is recorded in the database."
    ),
)
async def upload_contract(
    file: UploadFile = File(..., description="The contract PDF file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Validate file extension (only PDF allowed)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # 2. Read content and validate file size (max 10MB)
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # 3. Ensure uploads directory exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 4. Generate unique filename to avoid path traversal and collisions
    file_uuid = uuid.uuid4()
    original_filename = Path(file.filename).name
    unique_filename = f"{file_uuid}_{original_filename}"
    dest_path = upload_dir / unique_filename

    # 5. Save the file to disk
    try:
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}",
        )

    # 6. Create database record
    try:
        db_contract = Contract(
            user_id=current_user.id,
            filename=original_filename,
            upload_path=str(dest_path),
            status="pending",
        )
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
    except Exception as e:
        # Clean up file on DB failure
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save contract metadata: {str(e)}",
        )

    return db_contract


# ── GET /contracts/ ──────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[ContractResponse],
    summary="List user's contracts",
    description="Returns a list of all contracts uploaded by the currently authenticated user.",
)
async def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contracts = (
        db.query(Contract)
        .filter(Contract.user_id == current_user.id)
        .order_by(Contract.created_at.desc())
        .all()
    )
    return contracts


# ── GET /contracts/{contract_id} ─────────────────────────────────────────────

@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Get contract details",
    description="Retrieves the metadata of a specific contract by its ID. The contract must belong to the user.",
)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    return contract


# ── POST /contracts/{contract_id}/extract ──────────────────────────────────────

@router.post(
    "/{contract_id}/extract",
    response_model=TextExtractionResponse,
    summary="Extract text from contract PDF",
    description="Extracts raw text from the uploaded contract PDF and stores it in the analyses table.",
)
async def extract_contract_text(
    contract_id: int,
    strategy: str = "pymupdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.pdf_extractor import extract_pdf_text
    from app.models.analysis import Analysis

    # 1. Fetch contract
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

    # 2. Validate strategy query parameter
    if strategy not in ["pymupdf", "pdfplumber"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid strategy. Allowed options: 'pymupdf', 'pdfplumber'.",
        )

    # 3. Perform text extraction
    extracted = extract_pdf_text(contract.upload_path, strategy=strategy)

    # 4. Check if there is an existing raw_text analysis for this contract
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.contract_id == contract.id,
            Analysis.analysis_type == "raw_text",
        )
        .first()
    )

    result_json = {
        "text": extracted["text"],
        "page_count": extracted["page_count"],
        "is_scanned": extracted["is_scanned"],
        "strategy": extracted["strategy"],
    }

    if analysis:
        # Update existing record
        analysis.result_json = result_json
    else:
        # Create new record
        analysis = Analysis(
            contract_id=contract.id,
            analysis_type="raw_text",
            result_json=result_json,
        )
        db.add(analysis)

    # 5. Update contract status to 'ingested'
    contract.status = "ingested"
    db.commit()

    return TextExtractionResponse(
        contract_id=contract.id,
        page_count=extracted["page_count"],
        is_scanned=extracted["is_scanned"],
        strategy=extracted["strategy"],
        text=extracted["text"],
    )
