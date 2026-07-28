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
from app.agents.risk_agent import extract_risks_node, build_risk_graph, _clean_and_parse_json
from app.agents.base import ContractAnalysisState

client = TestClient(app)
TEST_EMAIL = "risk_test_user@example.com"

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
        "text": "Both parties agree to protect all information shared, including publicly available details.",
        "location": "middle",
        "present": True
    },
    "intellectual_property_clauses": {
        "text": "All intellectual property, including prior work, is assigned to the client.",
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

MOCK_RISK_RESPONSE = """
{
  "risks": [
    {
      "risk_type": "UNLIMITED_LIABILITY",
      "severity": "HIGH",
      "clause_text": "Provider's liability is unlimited under this agreement, and there is no cap on damages.",
      "explanation": "This clause exposes the provider to unlimited financial damages, which could lead to severe financial risk.",
      "suggestion": "Negotiate a liability cap equal to 1x or 2x the annual fees paid under the contract."
    },
    {
      "risk_type": "AUTOMATIC_RENEWAL",
      "severity": "MEDIUM",
      "clause_text": "This agreement will auto-renew forever without notice.",
      "explanation": "The contract automatically renews without notice, potentially locking you into terms you no longer want.",
      "suggestion": "Require written notice at least 30 days prior to the renewal date to prevent auto-renewal."
    },
    {
      "risk_type": "EXCESSIVE_PENALTIES",
      "severity": "HIGH",
      "clause_text": "Late payments shall accrue interest at 5% per month.",
      "explanation": "Interest of 5% per month (60% annually) is excessive and standard practice is around 1-1.5% per month.",
      "suggestion": "Request interest rates to be reduced to 1% or 1.5% per month."
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
            refresh_token_hash="risk-session-hash-123",
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
            filename="test_risk_agreement.pdf",
            upload_path="uploads/test_risk_agreement.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return f"Bearer {token}", contract.id, user.id
    finally:
        db.close()

def test_clean_and_parse_json_valid_risks():
    raw_json = """
    ```json
    {
      "risks": [
        {
          "risk_type": "UNLIMITED_LIABILITY",
          "severity": "HIGH",
          "clause_text": "Unlimited liability applies...",
          "explanation": "High financial risk.",
          "suggestion": "Negotiate cap."
        }
      ]
    }
    ```
    """
    parsed = _clean_and_parse_json(raw_json)
    assert "risks" in parsed
    assert len(parsed["risks"]) == 1
    assert parsed["risks"][0]["risk_type"] == "UNLIMITED_LIABILITY"
    assert parsed["risks"][0]["severity"] == "HIGH"

@patch("app.agents.risk_agent.get_llm_response")
def test_risk_agent_node_extraction(mock_get_llm):
    mock_get_llm.return_value = MOCK_RISK_RESPONSE
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": "Some raw text from the contract.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": SAMPLE_EXTRACTED_CLAUSES,
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }
    result = extract_risks_node(initial_state)
    assert "risks" in result
    risks = result["risks"]
    assert isinstance(risks, list)
    assert len(risks) == 3
    
    assert risks[0]["risk_type"] == "UNLIMITED_LIABILITY"
    assert risks[0]["severity"] == "HIGH"
    assert risks[1]["risk_type"] == "AUTOMATIC_RENEWAL"
    assert risks[2]["risk_type"] == "EXCESSIVE_PENALTIES"

@patch("app.agents.risk_agent.get_llm_response")
def test_risk_agent_graph_execution(mock_get_llm):
    mock_get_llm.return_value = MOCK_RISK_RESPONSE
    graph = build_risk_graph()
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": "Some raw text from the contract.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": SAMPLE_EXTRACTED_CLAUSES,
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }
    final_state = graph.invoke(initial_state)
    assert "risks" in final_state
    assert isinstance(final_state["risks"], list)
    assert len(final_state["risks"]) == 3
    assert len(final_state["messages"]) == 1
    assert final_state["error"] is None

@patch("app.agents.risk_agent.get_llm_response")
def test_run_risk_agent_endpoint(mock_get_llm):
    mock_get_llm.return_value = MOCK_RISK_RESPONSE
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

        # Call POST /contracts/{contract_id}/analyze/risks
        headers = {"Authorization": auth_header}
        response = client.post(f"/contracts/{contract_id}/analyze/risks", headers=headers)
        assert response.status_code == 200, f"Endpoint failed: {response.text}"
        
        data = response.json()
        assert data["contract_id"] == contract_id
        assert "risks" in data
        assert isinstance(data["risks"], list)
        assert len(data["risks"]) == 3
        
        # Verify the database state
        db.refresh(raw_analysis)
        db.refresh(clauses_analysis)
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "analyzed"
        
        risk_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "risks"
        ).first()
        assert risk_analysis is not None
        assert isinstance(risk_analysis.result_json, dict)
        assert "risks" in risk_analysis.result_json
        assert len(risk_analysis.result_json["risks"]) == 3
        assert risk_analysis.result_json["risks"][0]["risk_type"] == "UNLIMITED_LIABILITY"
    finally:
        db.close()
        cleanup_db()
