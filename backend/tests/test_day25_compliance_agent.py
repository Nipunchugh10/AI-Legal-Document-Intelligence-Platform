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
from app.agents.compliance_agent import check_compliance_node, build_compliance_graph, _clean_and_parse_json
from app.agents.base import ContractAnalysisState

client = TestClient(app)
TEST_EMAIL = "compliance_test_user@example.com"

SAMPLE_EXTRACTED_CLAUSES = {
    "payment_terms": {
        "text": "Client shall pay Provider a monthly fee of $8,000 USD within 10 days of invoice receipt. Late payments shall accrue interest at 5% per month.",
        "location": "beginning",
        "present": True
    },
    "termination_clauses": {
        "text": "Either party may terminate this Agreement for convenience by providing thirty (30) days written notice to the other party.",
        "location": "beginning",
        "present": True
    },
    "liability_clauses": {
        "text": "Provider's liability is unlimited under this agreement, and there is no cap on damages.",
        "location": "middle",
        "present": True
    },
    "confidentiality_clauses": {
        "text": "Both parties agree to protect all information shared, without exclusions.",
        "location": "middle",
        "present": True
    },
    "intellectual_property_clauses": {
        "text": "All intellectual property is assigned to the client.",
        "location": "middle",
        "present": True
    },
    "dispute_resolution_clauses": {
        "text": "Not mentioned",
        "location": "Not mentioned",
        "present": False
    },
    "governing_law_clauses": {
        "text": "Not mentioned",
        "location": "Not mentioned",
        "present": False
    },
    "renewal_clauses": {
        "text": "This agreement will auto-renew forever without notice.",
        "location": "end",
        "present": True
    },
    "indemnification_clauses": {
        "text": "Not mentioned",
        "location": "Not mentioned",
        "present": False
    }
}

MOCK_COMPLIANCE_RESPONSE = """
{
  "compliance_issues": [
    {
      "issue_type": "MISSING_REQUIRED_CLAUSE",
      "clause_type": "dispute_resolution",
      "severity": "MEDIUM",
      "explanation": "This contract has no dispute resolution mechanism, which can lead to costly court proceedings in case of conflicts.",
      "recommendation": "Add a clause specifying arbitration or mediation process under the Arbitration and Conciliation Act, 1996."
    },
    {
      "issue_type": "POTENTIALLY_ILLEGAL_TERM",
      "clause_type": "payment_terms",
      "severity": "HIGH",
      "explanation": "Late payments interest of 5% per month (60% annually) violates Section 74 penalty limits under Indian contract law, which only allows reasonable compensation.",
      "recommendation": "Reduce the late payment interest rate to a standard rate, typically between 1% to 1.5% per month."
    },
    {
      "issue_type": "DPDP_COMPLIANCE_ISSUE",
      "clause_type": "data_privacy",
      "severity": "HIGH",
      "explanation": "The contract does not specify a right to erasure or define Data Protection Officer (DPO) grievance redressal details for user personal data.",
      "recommendation": "Incorporate explicit data deletion obligations upon termination, and add contact details for grievance redressal under DPDP Act 2023."
    }
  ]
}
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
            refresh_token_hash="compliance-session-hash-123",
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
            filename="test_compliance_agreement.pdf",
            upload_path="uploads/test_compliance_agreement.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return f"Bearer {token}", contract.id, user.id
    finally:
        db.close()

def test_clean_and_parse_json_valid_compliance():
    raw_json = """
    ```json
    {
      "compliance_issues": [
        {
          "issue_type": "MISSING_REQUIRED_CLAUSE",
          "clause_type": "dispute_resolution",
          "severity": "MEDIUM",
          "explanation": "No dispute resolution.",
          "recommendation": "Add arbitration clause."
        }
      ]
    }
    ```
    """
    parsed = _clean_and_parse_json(raw_json)
    assert "compliance_issues" in parsed
    assert len(parsed["compliance_issues"]) == 1
    assert parsed["compliance_issues"][0]["issue_type"] == "MISSING_REQUIRED_CLAUSE"
    assert parsed["compliance_issues"][0]["severity"] == "MEDIUM"

@patch("app.agents.compliance_agent.get_llm_response")
def test_compliance_agent_node_check(mock_get_llm):
    mock_get_llm.return_value = MOCK_COMPLIANCE_RESPONSE
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": "Some raw text from the contract.",
        "chunks": [],
        "document_type": "Non-Disclosure Agreement (NDA)",
        "metadata": {},
        "clauses": SAMPLE_EXTRACTED_CLAUSES,
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }
    result = check_compliance_node(initial_state)
    assert "compliance_issues" in result
    issues = result["compliance_issues"]
    assert isinstance(issues, list)
    assert len(issues) == 3
    
    assert issues[0]["issue_type"] == "MISSING_REQUIRED_CLAUSE"
    assert issues[0]["clause_type"] == "dispute_resolution"
    assert issues[1]["issue_type"] == "POTENTIALLY_ILLEGAL_TERM"
    assert issues[2]["issue_type"] == "DPDP_COMPLIANCE_ISSUE"

@patch("app.agents.compliance_agent.get_llm_response")
def test_compliance_agent_graph_execution(mock_get_llm):
    mock_get_llm.return_value = MOCK_COMPLIANCE_RESPONSE
    graph = build_compliance_graph()
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": "Some raw text from the contract.",
        "chunks": [],
        "document_type": "Freelance Agreement",
        "metadata": {},
        "clauses": SAMPLE_EXTRACTED_CLAUSES,
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }
    final_state = graph.invoke(initial_state)
    assert "compliance_issues" in final_state
    assert isinstance(final_state["compliance_issues"], list)
    assert len(final_state["compliance_issues"]) == 3
    assert len(final_state["messages"]) == 1
    assert final_state["error"] is None

@patch("app.agents.compliance_agent.get_llm_response")
def test_run_compliance_agent_endpoint(mock_get_llm):
    mock_get_llm.return_value = MOCK_COMPLIANCE_RESPONSE
    auth_header, contract_id, user_id = setup_test_environment()
    db = SessionLocal()
    try:
        # Pre-seed raw text analysis
        raw_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="raw_text",
            result_json={
                "text": "Raw contract text context.",
                "page_count": 1,
                "is_scanned": False,
                "strategy": "pymupdf"
            }
        )
        db.add(raw_analysis)
        
        # Pre-seed clauses analysis
        clauses_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="clauses",
            result_json=SAMPLE_EXTRACTED_CLAUSES
        )
        db.add(clauses_analysis)
        db.commit()

        # Call POST /contracts/{contract_id}/analyze/compliance
        headers = {"Authorization": auth_header}
        response = client.post(f"/contracts/{contract_id}/analyze/compliance", headers=headers)
        assert response.status_code == 200, f"Endpoint failed: {response.text}"
        
        data = response.json()
        assert data["contract_id"] == contract_id
        assert "compliance_issues" in data
        assert isinstance(data["compliance_issues"], list)
        assert len(data["compliance_issues"]) == 3
        
        # Verify the database state
        db.refresh(raw_analysis)
        db.refresh(clauses_analysis)
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "analyzed"
        
        compliance_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "compliance"
        ).first()
        assert compliance_analysis is not None
        assert isinstance(compliance_analysis.result_json, dict)
        assert "compliance_issues" in compliance_analysis.result_json
        assert len(compliance_analysis.result_json["compliance_issues"]) == 3
        assert compliance_analysis.result_json["compliance_issues"][0]["issue_type"] == "MISSING_REQUIRED_CLAUSE"
    finally:
        db.close()
        cleanup_db()
