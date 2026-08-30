"""
Analysis Background Task Service
--------------------------------
Executes the full LangGraph multi-agent analysis workflow asynchronously in the background.
Persists intermediate findings and updates contract status upon completion or failure.

Day 42 — Async Background Processing
"""

import logging
from pathlib import Path
from typing import Any, Dict

from app.core.database import SessionLocal
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.agents.workflow import build_analysis_workflow
from app.agents.base import ContractAnalysisState
from app.services.pdf_extractor import extract_document_text

logger = logging.getLogger(__name__)


def _save_analysis_record(db, contract_id: int, analysis_type: str, result_payload: Any) -> None:
    """Helper function to create or update an analysis record in PostgreSQL."""
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
            result_json=result_payload,
        )
        db.add(record)


def run_analysis_workflow_task(contract_id: int, user_id: int) -> None:
    """
    Background worker task to execute the full LangGraph multi-agent analysis workflow.
    Uses an independent database session to track lifecycle state and persist findings.
    """
    logger.info("Starting background analysis workflow for contract_id=%s, user_id=%s", contract_id, user_id)
    db = SessionLocal()
    try:
        contract = (
            db.query(Contract)
            .filter(Contract.id == contract_id, Contract.user_id == user_id)
            .first()
        )
        if not contract:
            logger.error("Contract %s not found for user %s", contract_id, user_id)
            return

        # 1. Update contract status to 'processing'
        contract.status = "processing"
        db.commit()

        # 2. Retrieve or extract raw text
        raw_text_record = (
            db.query(Analysis)
            .filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "raw_text")
            .first()
        )
        if raw_text_record and raw_text_record.result_json and isinstance(raw_text_record.result_json, dict) and "text" in raw_text_record.result_json:
            raw_text = raw_text_record.result_json["text"]
        else:
            if not contract.upload_path or not Path(contract.upload_path).exists():
                logger.error("Upload path missing for contract %s: %s", contract_id, contract.upload_path)
                contract.status = "failed"
                _save_analysis_record(db, contract_id, "error", {"error": "Contract document file not found on disk"})
                db.commit()
                return

            extraction_res = extract_document_text(contract.upload_path)
            raw_text = extraction_res.get("text", "")
            _save_analysis_record(db, contract_id, "raw_text", extraction_res)
            db.commit()

        # 3. Prepare initial LangGraph state
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

        # 4. Execute LangGraph workflow
        workflow = build_analysis_workflow()
        final_state = workflow.invoke(initial_state)

        if final_state.get("error"):
            raw_err = str(final_state["error"])
            logger.error("LangGraph analysis error for contract %s: %s", contract_id, raw_err)
            contract.status = "failed"
            _save_analysis_record(db, contract_id, "error", {"error": raw_err})
            db.commit()
            return

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

        # 7. Update contract status to analyzed
        contract.status = "analyzed"
        db.commit()
        logger.info("Background analysis workflow completed successfully for contract_id=%s", contract_id)

    except Exception as exc:
        logger.exception("Unexpected exception in background analysis for contract_id=%s: %s", contract_id, exc)
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if contract:
                contract.status = "failed"
                _save_analysis_record(db, contract_id, "error", {"error": str(exc)})
                db.commit()
        except Exception as inner_exc:
            logger.error("Failed to persist failed status in db: %s", inner_exc)
    finally:
        db.close()
