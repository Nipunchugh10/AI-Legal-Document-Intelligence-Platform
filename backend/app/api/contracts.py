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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.user import User
from app.schemas.contract import (
    ContractResponse,
    TextExtractionResponse,
    ChunkingResponse,
    ParsingAgentResponse,
)

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


# ── POST /contracts/{contract_id}/chunk ─────────────────────────────────────────

@router.post(
    "/{contract_id}/chunk",
    response_model=ChunkingResponse,
    summary="Chunk extracted contract text",
    description="Loads the raw extracted text of a contract, normalizes and preprocesses it, splits it into tokens of specified chunk size/overlap, and stores the chunks in the analyses table.",
)
async def chunk_contract_text(
    contract_id: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.chunker import chunk_text
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

    # 2. Fetch raw text analysis
    raw_text_analysis = (
        db.query(Analysis)
        .filter(
            Analysis.contract_id == contract.id,
            Analysis.analysis_type == "raw_text",
        )
        .first()
    )
    if not raw_text_analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract text must be extracted first (run POST /contracts/{id}/extract).",
        )

    text = raw_text_analysis.result_json.get("text", "")
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extracted text is empty.",
        )

    # 3. Perform chunking
    try:
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing text chunking: {str(e)}",
        )

    # 4. Save chunks to analyses table
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.contract_id == contract.id,
            Analysis.analysis_type == "chunks",
        )
        .first()
    )

    result_json = {
        "chunk_count": len(chunks),
        "chunks": chunks,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }

    if analysis:
        # Update existing record
        analysis.result_json = result_json
    else:
        # Create new record
        analysis = Analysis(
            contract_id=contract.id,
            analysis_type="chunks",
            result_json=result_json,
        )
        db.add(analysis)

    db.commit()

    return ChunkingResponse(
        contract_id=contract.id,
        chunk_count=len(chunks),
        chunks=chunks,
    )


# ── POST /contracts/{contract_id}/ingest ────────────────────────────────────────

@router.post(
    "/{contract_id}/ingest",
    response_model=ContractResponse,
    summary="Ingest contract (PDF -> Chunks -> Embeddings -> Vector DB)",
    description="Triggers the complete end-to-end ingestion pipeline. By default, it runs in the background. Set background=false to run synchronously.",
)
async def ingest_contract_endpoint(
    contract_id: int,
    background_tasks: BackgroundTasks,
    background: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.ingestion_pipeline import ingest_contract

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

    if not background:
        # Run synchronously
        try:
            await ingest_contract(contract_id, db)
            db.refresh(contract)
            return contract
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion pipeline failed: {str(e)}",
            )

    # Run in background
    contract.status = "processing"
    db.commit()

    def run_ingestion():
        from app.core.database import SessionLocal
        bg_db = SessionLocal()
        try:
            import asyncio
            asyncio.run(ingest_contract(contract_id, bg_db))
        except Exception:
            pass
        finally:
            bg_db.close()

    background_tasks.add_task(run_ingestion)

    return contract


# ── DELETE /contracts/{contract_id} ─────────────────────────────────────────────

@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a contract",
    description="Deletes a contract record from database, its associated analyses, its vector embeddings in ChromaDB, and the raw PDF file from local storage.",
)
async def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os
    import logging
    from app.services.vector_store import get_vector_store_service

    logger = logging.getLogger(__name__)

    # 1. Fetch contract and check ownership
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

    # 2. Delete file from local storage
    if contract.upload_path:
        file_path = Path(contract.upload_path)
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"[+] Deleted local file: {file_path}")
            except Exception as e:
                logger.warning(f"[-] Could not delete contract file {file_path}: {e}")

    # 3. Delete embeddings from ChromaDB
    try:
        vector_store = get_vector_store_service()
        vector_store.delete_contract_chunks(contract_id)
        logger.info(f"[+] Deleted ChromaDB chunks for contract {contract_id}")
    except Exception as e:
        logger.warning(f"[-] Could not delete ChromaDB chunks for contract {contract_id}: {e}")

    # 4. Delete contract from PostgreSQL (cascades to analyses)
    try:
        db.delete(contract)
        db.commit()
        logger.info(f"[+] Deleted contract metadata from database for contract {contract_id}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete contract metadata: {str(e)}",
        )

    return {"status": "success", "message": f"Contract {contract_id} deleted successfully."}


# ── POST /contracts/{contract_id}/analyze/parse ─────────────────────────────

@router.post(
    "/{contract_id}/analyze/parse",
    response_model=ParsingAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Document Parsing Agent (Agent 1)",
    description=(
        "Parses contract text using LangGraph Document Parsing Agent 1 (Gemini LLM) "
        "to classify document type, extract key parties, effective date, jurisdiction, and executive summary."
    ),
)
async def run_parsing_agent(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.analysis import Analysis
    from app.services.pdf_extractor import extract_pdf_text
    from app.agents.parsing_agent import build_parsing_graph
    from app.agents.base import ContractAnalysisState

    # 1. Fetch contract & check ownership
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

    # 2. Get existing raw text or extract from file
    raw_text_record = (
        db.query(Analysis)
        .filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "raw_text")
        .first()
    )

    if raw_text_record and raw_text_record.result_json and "text" in raw_text_record.result_json:
        raw_text = raw_text_record.result_json["text"]
    else:
        if not contract.upload_path or not Path(contract.upload_path).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract file not found on disk to extract text.",
            )
        extraction_res = extract_pdf_text(contract.upload_path)
        raw_text = extraction_res["text"]
        new_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="raw_text",
            result_json=extraction_res,
        )
        db.add(new_analysis)
        db.commit()

    # 3. Prepare initial state & execute LangGraph parsing graph
    initial_state: ContractAnalysisState = {
        "contract_id": contract_id,
        "raw_text": raw_text,
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }

    parsing_graph = build_parsing_graph()
    final_state = parsing_graph.invoke(initial_state)

    if final_state.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing agent failed: {final_state['error']}",
        )

    doc_type = final_state.get("document_type", "Legal Document")
    metadata = final_state.get("metadata", {})
    party_a = metadata.get("party_a", "Not mentioned")
    party_b = metadata.get("party_b", "Not mentioned")
    effective_date = metadata.get("effective_date", "Not mentioned")
    jurisdiction = metadata.get("jurisdiction", "Not mentioned")
    summary = final_state.get("summary", "")

    # 4. Save analysis to database
    analysis_record = (
        db.query(Analysis)
        .filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "parsing_agent")
        .first()
    )
    analysis_payload = {
        "document_type": doc_type,
        "party_a": party_a,
        "party_b": party_b,
        "effective_date": effective_date,
        "jurisdiction": jurisdiction,
        "summary": summary,
    }

    if analysis_record:
        analysis_record.result_json = analysis_payload
    else:
        analysis_record = Analysis(
            contract_id=contract_id,
            analysis_type="parsing_agent",
            result_json=analysis_payload,
        )
        db.add(analysis_record)

    contract.status = "parsed"
    db.commit()

    return ParsingAgentResponse(
        contract_id=contract_id,
        document_type=doc_type,
        party_a=party_a,
        party_b=party_b,
        effective_date=effective_date,
        jurisdiction=jurisdiction,
        summary=summary,
    )



