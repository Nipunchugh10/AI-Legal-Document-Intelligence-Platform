import sys
import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.user_session import UserSession
from app.core.security import create_access_token
from app.agents.workflow import build_analysis_workflow, check_text_exists
from app.agents.base import ContractAnalysisState

client = TestClient(app)
TEST_EMAIL = "workflow_test_user@example.com"

# Mock responses for all agents in sequence
MOCK_PARSING_RESPONSE = """
{
  "document_type": "Non-Disclosure Agreement (NDA)",
  "party_a": "Alpha Corp",
  "party_b": "Beta LLC",
  "effective_date": "2026-08-04",
  "jurisdiction": "Delhi, India",
  "summary": "This is a mutual non-disclosure agreement protecting proprietary assets."
}
"""

MOCK_CLAUSES_RESPONSE = """
{
  "clauses": [
    {
      "clause_type": "payment_terms",
      "present": true,
      "text": "Beta LLC shall pay Alpha Corp within 30 days of invoice receipt.",
      "location": "beginning"
    },
    {
      "clause_type": "termination_clauses",
      "present": true,
      "text": "Either party may terminate for convenience with 30 days written notice.",
      "location": "middle"
    }
  ]
}
"""

MOCK_RISK_RESPONSE = """
{
  "risks": [
    {
      "risk_type": "ONE_SIDED_TERMINATION",
      "severity": "LOW",
      "clause_text": "Either party may terminate for convenience with 30 days written notice.",
      "explanation": "Standard mutual termination clause.",
      "suggestion": "Keep as is."
    }
  ]
}
"""

MOCK_NEGOTIATION_RESPONSE = """
[
  {
    "risk_type": "ONE_SIDED_TERMINATION",
    "clause_text": "Either party may terminate for convenience with 30 days written notice.",
    "suggested_revision": "Either party may terminate only for cause.",
    "negotiation_tip": "Push for cause-based termination."
  }
]
"""

MOCK_COMPLIANCE_RESPONSE = """
{
  "compliance_issues": [
    {
      "issue_type": "MISSING_REQUIRED_CLAUSE",
      "clause_type": "dispute_resolution",
      "severity": "MEDIUM",
      "explanation": "Missing dispute resolution.",
      "recommendation": "Add arbitration clause."
    }
  ]
}
"""

MOCK_SUMMARY_RESPONSE = """
### Executive Summary
This is an NDA between Alpha Corp and Beta LLC.

### Key Risk Highlights
- **Mutual termination for convenience** was flagged as low risk.

### Compliance Status
- Missing dispute resolution clause under Arbitration Act, 1996.

### Actionable Next Steps
1. Add an arbitration dispute resolution clause.
"""

def cleanup_db():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
            for c in contracts:
                db.query(Analysis).filter(Analysis.contract_id == c.id).delete()
                db.delete(c)
            db.query(UserSession).filter(UserSession.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()

def setup_test_environment() -> tuple[str, int, int]:
    cleanup_db()
    db = SessionLocal()
    try:
        user = User(
            email=TEST_EMAIL,
            hashed_password="some-hashed-password",
            is_active=True,
            is_2fa_enabled=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash="wf-session-hash-123",
            device_info="Test Browser",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        contract = Contract(
            user_id=user.id,
            filename="test_workflow_agreement.pdf",
            upload_path="uploads/test_workflow_agreement.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return f"Bearer {token}", contract.id, user.id
    finally:
        db.close()

def test_conditional_routing_text_exists():
    state_ok: ContractAnalysisState = {
        "contract_id": 1,
        "raw_text": "Valid contract text.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None
    }
    assert check_text_exists(state_ok) == "parse_document"

def test_conditional_routing_text_missing():
    state_fail: ContractAnalysisState = {
        "contract_id": 1,
        "raw_text": "",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None
    }
    assert check_text_exists(state_fail) == "error_node"

@patch("app.agents.parsing_agent.get_llm_response")
@patch("app.agents.clause_agent.get_llm_response")
@patch("app.agents.risk_agent.get_llm_response")
@patch("app.agents.negotiation_agent.get_llm_response")
@patch("app.agents.compliance_agent.get_llm_response")
@patch("app.agents.workflow.get_llm_response")
@patch("app.agents.clause_agent.get_vector_store_service")
@patch("app.agents.compliance_agent.get_vector_store_service")
def test_full_workflow_execution(
    mock_vs_comp, mock_vs_clause, mock_summary, mock_comp, mock_neg, mock_risk, mock_clause, mock_parse
):
    # Mock LLM returns
    mock_parse.return_value = MOCK_PARSING_RESPONSE
    mock_clause.return_value = MOCK_CLAUSES_RESPONSE
    mock_risk.return_value = MOCK_RISK_RESPONSE
    mock_neg.return_value = MOCK_NEGOTIATION_RESPONSE
    mock_comp.return_value = MOCK_COMPLIANCE_RESPONSE
    mock_summary.return_value = MOCK_SUMMARY_RESPONSE

    # Mock Vector Store returns empty search lists
    mock_vs_comp.return_value.query_knowledge.return_value = []
    mock_vs_clause.return_value.query_contract_chunks.return_value = []

    workflow = build_analysis_workflow()
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": "This is raw contract text for Alpha Corp and Beta LLC.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None
    }

    final_state = workflow.invoke(initial_state)
    assert final_state["error"] is None
    assert final_state["document_type"] == "Non-Disclosure Agreement (NDA)"
    assert final_state["metadata"]["party_a"] == "Alpha Corp"
    assert final_state["clauses"]["payment_terms"]["present"] is True
    assert len(final_state["risks"]) == 1
    assert len(final_state["compliance_issues"]) == 1
    assert "dispute resolution" in final_state["summary"].lower()

@patch("app.agents.parsing_agent.get_llm_response")
@patch("app.agents.clause_agent.get_llm_response")
@patch("app.agents.risk_agent.get_llm_response")
@patch("app.agents.negotiation_agent.get_llm_response")
@patch("app.agents.compliance_agent.get_llm_response")
@patch("app.agents.workflow.get_llm_response")
@patch("app.agents.clause_agent.get_vector_store_service")
@patch("app.agents.compliance_agent.get_vector_store_service")
def test_analysis_workflow_endpoint(
    mock_vs_comp, mock_vs_clause, mock_summary, mock_comp, mock_neg, mock_risk, mock_clause, mock_parse
):
    # Mock LLM returns
    mock_parse.return_value = MOCK_PARSING_RESPONSE
    mock_clause.return_value = MOCK_CLAUSES_RESPONSE
    mock_risk.return_value = MOCK_RISK_RESPONSE
    mock_neg.return_value = MOCK_NEGOTIATION_RESPONSE
    mock_comp.return_value = MOCK_COMPLIANCE_RESPONSE
    mock_summary.return_value = MOCK_SUMMARY_RESPONSE

    # Mock Vector Store returns empty list
    mock_vs_comp.return_value.query_knowledge.return_value = []
    mock_vs_clause.return_value.query_contract_chunks.return_value = []

    auth_header, contract_id, user_id = setup_test_environment()
    db = SessionLocal()
    
    try:
        # Pre-seed raw text analysis
        raw_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="raw_text",
            result_json={
                "text": "This is raw contract text for Alpha Corp and Beta LLC.",
                "page_count": 1,
                "is_scanned": False,
                "strategy": "pymupdf"
            }
        )
        db.add(raw_analysis)
        db.commit()

        # Call POST /contracts/{contract_id}/analyze
        headers = {"Authorization": auth_header}
        response = client.post(f"/contracts/{contract_id}/analyze", headers=headers)
        assert response.status_code == 200, f"Endpoint failed: {response.text}"
        
        data = response.json()
        assert data["contract_id"] == contract_id
        assert data["document_type"] == "Non-Disclosure Agreement (NDA)"
        assert data["metadata"]["party_a"] == "Alpha Corp"
        assert len(data["risks"]) == 1
        assert "dispute resolution" in data["summary"].lower()

        # Verify DB records got populated for the 5 agents
        parsing_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "parsing_agent").first()
        clauses_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "clauses").first()
        risks_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "risks").first()
        comp_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "compliance").first()
        summary_rec = db.query(Analysis).filter(Analysis.contract_id == contract_id, Analysis.analysis_type == "summary").first()

        assert parsing_rec is not None
        assert clauses_rec is not None
        assert risks_rec is not None
        assert comp_rec is not None
        assert summary_rec is not None

        assert risks_rec.result_json["risks"][0]["risk_type"] == "ONE_SIDED_TERMINATION"
        assert comp_rec.result_json["compliance_issues"][0]["issue_type"] == "MISSING_REQUIRED_CLAUSE"
        assert "dispute resolution" in summary_rec.result_json["summary"].lower()

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "analyzed"
    finally:
        db.close()
        cleanup_db()
