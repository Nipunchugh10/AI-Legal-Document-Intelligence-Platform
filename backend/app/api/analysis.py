from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.contract import AnalysisWorkflowResponse
from app.agents.workflow import build_analysis_workflow
from app.agents.base import ContractAnalysisState
from app.services.pdf_extractor import extract_pdf_text
from app.services.analysis_task import run_analysis_workflow_task

router = APIRouter()

def _save_analysis_record(db: Session, contract_id: int, analysis_type: str, result_payload: Any) -> None:
    """Helper function to create or update an analysis record in the database."""
    record = (
        db.query(Analysis)
        .filter(Analysis.contract_id == contract_id, Analysis.analysis_type == analysis_type)
        .first()
    )
    if record:
        record.result_json = result_payload
    else:
        record = Analysis(
            contract_id=contract_id,
            analysis_type=analysis_type,
            result_json=result_payload
        )
        db.add(record)

@router.post(
    "/{contract_id}/analyze",
    response_model=AnalysisWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Run full contract analysis workflow (Async Background Processing)",
    description=(
        "Executes the full contract analysis orchestrator LangGraph. "
        "By default, runs in background via BackgroundTasks, setting contract status to 'processing'. "
        "Pass sync=true to execute synchronously."
    ),
)
async def run_full_analysis(
    contract_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    sync: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("Starting analysis for contract_id=%s", contract_id)
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

    # 2. Check cache (database) to bypass expensive LLM calls if all analyses exist
    if not force:
        target_types = ["parsing_agent", "clauses", "risks", "compliance", "summary"]
        records = (
            db.query(Analysis)
            .filter(Analysis.contract_id == contract_id, Analysis.analysis_type.in_(target_types))
            .all()
        )
        res_map = {r.analysis_type: r.result_json for r in records if isinstance(r.result_json, dict)}

        if len(res_map) == 5:
            p_res = res_map.get("parsing_agent", {})
            return AnalysisWorkflowResponse(
                contract_id=contract_id,
                status=contract.status or "analyzed",
                document_type=p_res.get("document_type", "Legal Contract"),
                metadata={
                    "party_a": p_res.get("party_a", "Not mentioned"),
                    "party_b": p_res.get("party_b", "Not mentioned"),
                    "effective_date": p_res.get("effective_date", "Not mentioned"),
                    "jurisdiction": p_res.get("jurisdiction", "Not mentioned"),
                },
                clauses=res_map.get("clauses", {}),
                risks=res_map.get("risks", {}).get("risks", []) if isinstance(res_map.get("risks"), dict) else [],
                compliance_issues=res_map.get("compliance", {}).get("compliance_issues", []) if isinstance(res_map.get("compliance"), dict) else [],
                summary=res_map.get("summary", {}).get("summary", "") if isinstance(res_map.get("summary"), dict) else "",
            )

    # 3. Async Background Task Mode (Default)
    if not sync:
        contract.status = "processing"
        db.commit()
        background_tasks.add_task(run_analysis_workflow_task, contract_id, current_user.id)
        return AnalysisWorkflowResponse(
            contract_id=contract_id,
            status="processing",
            document_type="Analyzing...",
            metadata={
                "party_a": "Analyzing...",
                "party_b": "Analyzing...",
                "effective_date": "Analyzing...",
                "jurisdiction": "Analyzing...",
            },
            clauses={},
            risks=[],
            compliance_issues=[],
            summary="Contract analysis has been queued and is executing in the background. Poll GET /contracts/{id} or /contracts/{id}/analysis for progress.",
        )

    # 4. Synchronous Mode (sync=True)
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

    # 4. Prepare initial state & execute LangGraph orchestrator graph
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

    workflow = build_analysis_workflow()
    final_state = workflow.invoke(initial_state)

    if final_state.get("error"):
        raw_err = str(final_state["error"])
        if "429" in raw_err or "quota" in raw_err.lower() or "ResourceExhausted" in raw_err:
            clean_err = "Google AI quota limit reached. Please wait a moment and try again."
        elif "503" in raw_err:
            clean_err = "AI service temporarily busy. Please retry in a few moments."
        else:
            clean_err = f"Analysis failed: {raw_err[:150]}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=clean_err,
        )

    # 5. Extract findings from final state
    doc_type = final_state.get("document_type", "Legal Document")
    metadata = final_state.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    party_a = str(metadata.get("party_a", "Not mentioned"))
    party_b = str(metadata.get("party_b", "Not mentioned"))
    effective_date = str(metadata.get("effective_date", "Not mentioned"))
    jurisdiction = str(metadata.get("jurisdiction", "Not mentioned"))
    
    clauses = final_state.get("clauses", {})
    if not isinstance(clauses, dict):
        clauses = {}
    risks = final_state.get("risks", [])
    if not isinstance(risks, list):
        risks = []
    compliance = final_state.get("compliance_issues", [])
    if not isinstance(compliance, list):
        compliance = []
    summary = str(final_state.get("summary", ""))

    # 6. Save each finding back to the PostgreSQL database
    parsing_payload = {
        "document_type": doc_type,
        "party_a": party_a,
        "party_b": party_b,
        "effective_date": effective_date,
        "jurisdiction": jurisdiction,
        "summary": summary[:200] if summary else "Parsing complete.",
    }
    
    _save_analysis_record(db, contract_id, "parsing_agent", parsing_payload)
    _save_analysis_record(db, contract_id, "clauses", clauses)
    _save_analysis_record(db, contract_id, "risks", {"risks": risks})
    _save_analysis_record(db, contract_id, "compliance", {"compliance_issues": compliance})
    _save_analysis_record(db, contract_id, "summary", {"summary": summary})

    # Update contract status to analyzed
    contract.status = "analyzed"
    db.commit()

    return AnalysisWorkflowResponse(
        contract_id=contract_id,
        status="analyzed",
        document_type=doc_type,
        metadata={
            "party_a": party_a,
            "party_b": party_b,
            "effective_date": effective_date,
            "jurisdiction": jurisdiction,
        },
        clauses=clauses,
        risks=risks,
        compliance_issues=compliance,
        summary=summary,
    )


@router.get(
    "/{contract_id}/analysis",
    response_model=AnalysisWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get existing analysis results for a contract (Optimized Batch & Memory Cached)",
)
async def get_contract_analysis(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves persisted analysis findings with in-memory caching and single-query batching."""
    from app.core.cache import memory_cache
    cache_key = f"analysis:{current_user.id}:{contract_id}"
    cached_response = memory_cache.get(cache_key)
    if cached_response:
        return cached_response

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

    # Single-batch query for all 5 analysis records (N+1 Optimization)
    target_types = ["parsing_agent", "clauses", "risks", "compliance", "summary"]
    records = (
        db.query(Analysis)
        .filter(Analysis.contract_id == contract_id, Analysis.analysis_type.in_(target_types))
        .all()
    )
    res_map = {r.analysis_type: r.result_json for r in records if isinstance(r.result_json, dict)}

    if not res_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis found for this contract. Please run analysis first.",
        )

    p_res = res_map.get("parsing_agent", {})
    c_res = res_map.get("clauses", {})
    r_res = res_map.get("risks", {})
    comp_res = res_map.get("compliance", {})
    s_res = res_map.get("summary", {})

    response = AnalysisWorkflowResponse(
        contract_id=contract_id,
        status=contract.status,
        document_type=p_res.get("document_type", "Legal Contract"),
        metadata={
            "party_a": p_res.get("party_a", "Not mentioned"),
            "party_b": p_res.get("party_b", "Not mentioned"),
            "effective_date": p_res.get("effective_date", "Not mentioned"),
            "jurisdiction": p_res.get("jurisdiction", "Not mentioned"),
        },
        clauses=c_res,
        risks=r_res.get("risks", []) if isinstance(r_res, dict) else [],
        compliance_issues=comp_res.get("compliance_issues", []) if isinstance(comp_res, dict) else [],
        summary=s_res.get("summary", "") if isinstance(s_res, dict) else "",
    )

    if contract.status == "analyzed":
        memory_cache.set(cache_key, response, ttl_seconds=300)

    return response


@router.get(
    "/{contract_id}/text",
    status_code=status.HTTP_200_OK,
    summary="Get raw extracted text of contract",
)
async def get_contract_text(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the extracted raw text for a contract document."""
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.user_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found.")

    raw_text_record = (
        db.query(Analysis)
        .filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "raw_text")
        .first()
    )
    if raw_text_record and raw_text_record.result_json and isinstance(raw_text_record.result_json, dict) and "text" in raw_text_record.result_json:
        return {"contract_id": contract_id, "text": raw_text_record.result_json["text"]}

    if contract.upload_path and Path(contract.upload_path).exists():
        from app.services.pdf_extractor import extract_document_text
        res = extract_document_text(contract.upload_path)
        return {"contract_id": contract_id, "text": res.get("text", "")}

    return {"contract_id": contract_id, "text": ""}
