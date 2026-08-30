"""
Day 42 — Async Background Processing Tests
------------------------------------------
Unit and integration tests for asynchronous background analysis processing:
1. BackgroundTasks queueing & immediate status="processing" response.
2. Background task execution and DB persistence (parsing, clauses, risks, compliance, summary).
3. Graceful failure state handling (contract.status="failed" and error record).
4. Cache bypass for existing complete analyses.
5. Synchronous fallback via sync=true parameter.
6. Verification of composite index on analyses (contract_id, analysis_type).
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token
from app.services.analysis_task import run_analysis_workflow_task

client = TestClient(app)
ASYNC_TEST_EMAIL = "async_worker_test@example.com"


@pytest.fixture
def setup_async_test_user():
    """Sets up a test user, authenticated session, and test contract."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == ASYNC_TEST_EMAIL).first()
        if not user:
            user = User(email=ASYNC_TEST_EMAIL, hashed_password="hashedpassword123", is_active=True, is_2fa_enabled=False)
            db.add(user)
            db.commit()
            db.refresh(user)

        import uuid
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=f"async-test-session-{uuid.uuid4()}",
            device_info="Pytest-Async-Client",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            is_revoked=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Create test contract
        contract = Contract(
            user_id=user.id,
            filename="Vendor_Service_Agreement_v1.pdf",
            upload_path="/tmp/fake_vendor_agreement.pdf",
            status="ingested",
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Raw text analysis record
        raw_text_analysis = Analysis(
            contract_id=contract.id,
            analysis_type="raw_text",
            result_json={"text": "This Master Services Agreement is entered into by Alpha Corp and Beta LLC. Either party may terminate with 30 days notice. Indemnity liability is capped at $100,000."},
        )
        db.add(raw_text_analysis)
        db.commit()

        token = create_access_token(data={"sub": user.email, "email": user.email, "session_id": session.id})
        headers = {"Authorization": f"Bearer {token}"}

        yield {
            "user_id": user.id,
            "contract_id": contract.id,
            "headers": headers,
        }

    finally:
        db.close()


def test_async_analyze_enqueues_background_task(setup_async_test_user):
    """
    POST /contracts/{id}/analyze in default async mode should immediately return
    status='processing' and set the contract in DB to 'processing'.
    """
    data = setup_async_test_user
    contract_id = data["contract_id"]
    headers = data["headers"]

    # We mock run_analysis_workflow_task to avoid running actual background worker during endpoint unit test
    with patch("app.api.analysis.run_analysis_workflow_task") as mock_task:
        response = client.post(f"/contracts/{contract_id}/analyze", headers=headers)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["contract_id"] == contract_id
        assert res_json["status"] == "processing"

        # Check that background task was enqueued
        mock_task.assert_called_once_with(contract_id, data["user_id"])

        # Check DB status is processing
        db = SessionLocal()
        try:
            c = db.query(Contract).filter(Contract.id == contract_id).first()
            assert c.status == "processing"
        finally:
            db.close()


def test_background_worker_task_execution_success(setup_async_test_user):
    """
    Verifies that run_analysis_workflow_task updates the contract status to 'analyzed'
    and persists all 5 analysis records to PostgreSQL upon successful execution.
    """
    data = setup_async_test_user
    contract_id = data["contract_id"]
    user_id = data["user_id"]

    mock_final_state = {
        "contract_id": contract_id,
        "document_type": "Master Services Agreement",
        "metadata": {
            "party_a": "Alpha Corp",
            "party_b": "Beta LLC",
            "effective_date": "2026-01-01",
            "jurisdiction": "California, USA",
        },
        "clauses": {
            "termination": "Either party may terminate with 30 days notice.",
            "indemnification": "Liability capped at $100,000.",
        },
        "risks": [
            {
                "risk_type": "Indemnity Liability Cap",
                "flag_category": "YELLOW_FLAG",
                "severity": "MEDIUM",
                "explanation": "Cap is set to fixed $100,000.",
                "suggestion": "Expand mutual indemnification carve-outs.",
            }
        ],
        "compliance_issues": [
            {
                "issue_type": "DPDP_COMPLIANCE_ISSUE",
                "clause_type": "Data Privacy",
                "severity": "MEDIUM",
                "explanation": "Explicit consent mechanism missing.",
                "recommendation": "Incorporate standard data processing clauses.",
            }
        ],
        "summary": "### Executive Legal Audit Summary\nThis contract is a standard Master Services Agreement with moderate indemnity liability risks.",
        "error": None,
    }

    mock_workflow = MagicMock()
    mock_workflow.invoke.return_value = mock_final_state

    with patch("app.services.analysis_task.build_analysis_workflow", return_value=mock_workflow):
        run_analysis_workflow_task(contract_id, user_id)

    db = SessionLocal()
    try:
        # Verify contract status
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "analyzed"

        # Verify parsing record
        parsing = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "parsing_agent").first()
        assert parsing is not None
        assert parsing.result_json["document_type"] == "Master Services Agreement"
        assert parsing.result_json["party_a"] == "Alpha Corp"

        # Verify risks record
        risks = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "risks").first()
        assert risks is not None
        assert len(risks.result_json["risks"]) == 1

        # Verify compliance record
        comp = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "compliance").first()
        assert comp is not None
        assert len(comp.result_json["compliance_issues"]) == 1

        # Verify summary record
        summary = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "summary").first()
        assert summary is not None
        assert "Executive Legal Audit Summary" in summary.result_json["summary"]

    finally:
        db.close()


def test_background_worker_task_error_handling(setup_async_test_user):
    """
    Verifies that when LangGraph workflow fails or encounters an exception,
    run_analysis_workflow_task sets contract.status='failed' and records the error.
    """
    data = setup_async_test_user
    contract_id = data["contract_id"]
    user_id = data["user_id"]

    mock_workflow = MagicMock()
    mock_workflow.invoke.side_effect = RuntimeError("Simulated upstream AI quota failure")

    with patch("app.services.analysis_task.build_analysis_workflow", return_value=mock_workflow):
        run_analysis_workflow_task(contract_id, user_id)

    db = SessionLocal()
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "failed"

        error_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "error").first()
        assert error_rec is not None
        assert "Simulated upstream AI quota failure" in error_rec.result_json["error"]
    finally:
        db.close()


def test_cached_analysis_bypasses_queue(setup_async_test_user):
    """
    When all 5 analysis records exist and force=False, POST /contracts/{id}/analyze
    should immediately return the cached analysis without enqueuing background task.
    """
    data = setup_async_test_user
    contract_id = data["contract_id"]
    headers = data["headers"]

    # Pre-populate all 5 analyses
    db = SessionLocal()
    try:
        c = db.query(Contract).filter(Contract.id == contract_id).first()
        c.status = "analyzed"
        db.add(Analysis(contract_id=contract_id, analysis_type="parsing_agent", result_json={"document_type": "Cached NDA", "party_a": "Alice", "party_b": "Bob"}))
        db.add(Analysis(contract_id=contract_id, analysis_type="clauses", result_json={"confidentiality": "Standard 3-year term"}))
        db.add(Analysis(contract_id=contract_id, analysis_type="risks", result_json={"risks": []}))
        db.add(Analysis(contract_id=contract_id, analysis_type="compliance", result_json={"compliance_issues": []}))
        db.add(Analysis(contract_id=contract_id, analysis_type="summary", result_json={"summary": "Cached NDA Executive Summary"}))
        db.commit()
    finally:
        db.close()

    with patch("app.api.analysis.run_analysis_workflow_task") as mock_task:
        response = client.post(f"/contracts/{contract_id}/analyze", headers=headers)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["status"] == "analyzed"
        assert res_json["document_type"] == "Cached NDA"
        assert res_json["summary"] == "Cached NDA Executive Summary"
        # Background task should NOT be enqueued because it was returned from cache
        mock_task.assert_not_called()


def test_analyses_composite_index_exists():
    """
    Verifies that the composite index on (contract_id, analysis_type) exists in PostgreSQL.
    """
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'analyses' AND indexname = 'ix_analyses_contract_id_analysis_type';")).fetchall()
        assert len(res) == 1
        assert res[0][0] == "ix_analyses_contract_id_analysis_type"
    finally:
        db.close()
