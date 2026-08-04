from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Any

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.contract import AnalysisWorkflowResponse
from app.agents.workflow import build_analysis_workflow
from app.agents.base import ContractAnalysisState
from app.services.pdf_extractor import extract_pdf_text

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
    summary="Run full contract analysis workflow",
    description=(
        "Executes the full contract analysis orchestrator LangGraph, combining "
        "document type classification, clause extraction, risk assessment, compliance checks, "
        "and executive summary generation into a single end-to-end pipeline."
    ),
)
async def run_full_analysis(
    contract_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    parsing_record = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "parsing_agent").first()
    clauses_record = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "clauses").first()
    risks_record = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "risks").first()
    compliance_record = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "compliance").first()
    summary_record = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "summary").first()

    if not force and parsing_record and clauses_record and risks_record and compliance_record and summary_record:
        p_res = parsing_record.result_json
        return AnalysisWorkflowResponse(
            contract_id=contract_id,
            status=contract.status,
            document_type=p_res.get("document_type", "Legal Contract"),
            metadata={
                "party_a": p_res.get("party_a", "Not mentioned"),
                "party_b": p_res.get("party_b", "Not mentioned"),
                "effective_date": p_res.get("effective_date", "Not mentioned"),
                "jurisdiction": p_res.get("jurisdiction", "Not mentioned"),
            },
            clauses=clauses_record.result_json,
            risks=risks_record.result_json.get("risks", []),
            compliance_issues=compliance_record.result_json.get("compliance_issues", []),
            summary=summary_record.result_json.get("summary", ""),
        )

    # 3. Retrieve raw text analysis or extract if missing
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis workflow failed: {final_state['error']}",
        )

    # 5. Extract findings from final state
    doc_type = final_state.get("document_type", "Legal Document")
    metadata = final_state.get("metadata", {})
    party_a = metadata.get("party_a", "Not mentioned")
    party_b = metadata.get("party_b", "Not mentioned")
    effective_date = metadata.get("effective_date", "Not mentioned")
    jurisdiction = metadata.get("jurisdiction", "Not mentioned")
    
    clauses = final_state.get("clauses", {})
    risks = final_state.get("risks", [])
    compliance = final_state.get("compliance_issues", [])
    summary = final_state.get("summary", "")

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
