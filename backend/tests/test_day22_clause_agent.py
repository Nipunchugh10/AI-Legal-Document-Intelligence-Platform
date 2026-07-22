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
from app.agents.clause_agent import extract_clauses_node, build_clause_graph, _clean_and_parse_json
from app.agents.base import ContractAnalysisState

client = TestClient(app)
TEST_EMAIL = "clause_test_user@example.com"

SAMPLE_CONTRACT_WITH_CLAUSES = """
SERVICE AGREEMENT
This Service Agreement is entered into on July 1, 2026, by and between Apex Corp ("Client") and DevConsultants LLC ("Provider").

1. PAYMENT TERMS: Client shall pay Provider a monthly fee of $8,000 USD within 10 days of invoice receipt. Late payments shall accrue interest at 1.5% per month.
2. TERM AND TERMINATION: This Agreement shall commence on the Effective Date and remain in effect for one (1) year. Either party may terminate this Agreement for convenience by providing thirty (30) days written notice to the other party.
3. LIABILITY: In no event shall either party be liable to the other for indirect, special, or consequential damages. Provider's maximum aggregate liability under this Agreement shall be capped at the total amount paid by Client under this Agreement in the twelve months preceding the claim.
4. CONFIDENTIALITY: Both parties agree to protect and keep confidential all non-public information disclosed during the term of this agreement. Confidential information does not include information that is publicly known.
5. INTELLECTUAL PROPERTY: All intellectual property, designs, patents, trademarks, and copyrights developed by Provider specifically for Client under this Agreement shall belong solely to the Client upon full payment of fees.
6. DISPUTE RESOLUTION: Any disputes arising out of this Agreement shall be resolved through binding arbitration in Wilmington, Delaware, under the rules of the American Arbitration Association.
7. GOVERNING LAW: This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles.
8. RENEWAL: This Agreement will automatically renew for successive one-year terms unless either party gives notice of non-renewal at least sixty (60) days prior to the end of the current term.
9. INDEMNIFICATION: Provider agrees to indemnify, defend, and hold harmless Client from and against any third-party claims alleging that the services infringe any intellectual property rights of a third party.
"""

MOCK_LLM_RESPONSE = """
{
  "clauses": [
    {
      "clause_type": "payment_terms",
      "present": true,
      "text": "Client shall pay Provider a monthly fee of $8,000 USD within 10 days of invoice receipt.",
      "location": "beginning"
    },
    {
      "clause_type": "termination_clauses",
      "present": true,
      "text": "Either party may terminate this Agreement for convenience by providing thirty (30) days written notice to the other party.",
      "location": "beginning"
    },
    {
      "clause_type": "liability_clauses",
      "present": true,
      "text": "Provider's maximum aggregate liability under this Agreement shall be capped at the total amount paid by Client under this Agreement in the twelve months preceding the claim.",
      "location": "middle"
    },
    {
      "clause_type": "confidentiality_clauses",
      "present": true,
      "text": "Both parties agree to protect and keep confidential all non-public information disclosed during the term of this agreement.",
      "location": "middle"
    },
    {
      "clause_type": "intellectual_property_clauses",
      "present": true,
      "text": "All intellectual property... developed by Provider specifically for Client... shall belong solely to the Client upon full payment of fees.",
      "location": "middle"
    },
    {
      "clause_type": "dispute_resolution_clauses",
      "present": true,
      "text": "Any disputes arising out of this Agreement shall be resolved through binding arbitration in Wilmington, Delaware...",
      "location": "end"
    },
    {
      "clause_type": "governing_law_clauses",
      "present": true,
      "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware...",
      "location": "end"
    },
    {
      "clause_type": "renewal_clauses",
      "present": true,
      "text": "This Agreement will automatically renew for successive one-year terms unless either party gives notice of non-renewal...",
      "location": "end"
    },
    {
      "clause_type": "indemnification_clauses",
      "present": true,
      "text": "Provider agrees to indemnify, defend, and hold harmless Client from and against any third-party claims...",
      "location": "end"
    }
  ]
}
"""

def cleanup_db():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            # Delete associated analyses and contracts
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
            refresh_token_hash="clause-session-hash-123",
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
            filename="test_clause_agreement.pdf",
            upload_path="uploads/test_clause_agreement.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return f"Bearer {token}", contract.id, user.id
    finally:
        db.close()

def test_clean_and_parse_json_valid_clauses():
    raw_json = """
    ```json
    {
      "clauses": [
        {
          "clause_type": "payment_terms",
          "present": true,
          "text": "Client shall pay $8,000 USD monthly",
          "location": "beginning"
        },
        {
          "clause_type": "confidentiality_clauses",
          "present": false,
          "text": "Not mentioned",
          "location": "Not mentioned"
        }
      ]
    }
    ```
    """
    parsed = _clean_and_parse_json(raw_json)
    assert "clauses" in parsed
    assert len(parsed["clauses"]) == 2
    assert parsed["clauses"][0]["clause_type"] == "payment_terms"
    assert parsed["clauses"][0]["present"] is True

@patch("app.services.vector_store.VectorStoreService.query_contract_chunks")
@patch("app.agents.clause_agent.get_llm_response")
def test_clause_agent_node_extraction(mock_get_llm, mock_query_chunks):
    mock_query_chunks.return_value = []
    mock_get_llm.return_value = MOCK_LLM_RESPONSE
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": SAMPLE_CONTRACT_WITH_CLAUSES,
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
    result = extract_clauses_node(initial_state)
    assert "clauses" in result
    clauses = result["clauses"]
    assert isinstance(clauses, dict)
    
    target_types = [
        "payment_terms",
        "termination_clauses",
        "liability_clauses",
        "confidentiality_clauses",
        "intellectual_property_clauses",
        "dispute_resolution_clauses",
        "governing_law_clauses",
        "renewal_clauses",
        "indemnification_clauses"
    ]
    for t in target_types:
        assert t in clauses
        assert "text" in clauses[t]
        assert "location" in clauses[t]
        assert "present" in clauses[t]

@patch("app.services.vector_store.VectorStoreService.query_contract_chunks")
@patch("app.agents.clause_agent.get_llm_response")
def test_clause_agent_graph_execution(mock_get_llm, mock_query_chunks):
    mock_query_chunks.return_value = []
    mock_get_llm.return_value = MOCK_LLM_RESPONSE
    graph = build_clause_graph()
    initial_state: ContractAnalysisState = {
        "contract_id": 9999,
        "raw_text": SAMPLE_CONTRACT_WITH_CLAUSES,
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
    final_state = graph.invoke(initial_state)
    assert "clauses" in final_state
    assert isinstance(final_state["clauses"], dict)
    assert len(final_state["messages"]) == 1
    assert final_state["error"] is None

@patch("app.services.vector_store.VectorStoreService.query_contract_chunks")
@patch("app.agents.clause_agent.get_llm_response")
def test_run_clause_agent_endpoint(mock_get_llm, mock_query_chunks):
    mock_query_chunks.return_value = []
    mock_get_llm.return_value = MOCK_LLM_RESPONSE
    auth_header, contract_id, user_id = setup_test_environment()
    db = SessionLocal()
    try:
        # Pre-seed raw text analysis so the endpoint doesn't try to extract from a non-existent PDF file
        raw_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="raw_text",
            result_json={
                "text": SAMPLE_CONTRACT_WITH_CLAUSES,
                "page_count": 1,
                "is_scanned": False,
                "strategy": "pymupdf"
            }
        )
        db.add(raw_analysis)
        db.commit()

        # Call POST /contracts/{contract_id}/analyze/clauses
        headers = {"Authorization": auth_header}
        response = client.post(f"/contracts/{contract_id}/analyze/clauses", headers=headers)
        assert response.status_code == 200, f"Endpoint failed: {response.text}"
        
        data = response.json()
        assert data["contract_id"] == contract_id
        assert "clauses" in data
        assert isinstance(data["clauses"], dict)
        
        # Verify the database state
        db.refresh(raw_analysis)
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.status == "analyzed"
        
        clause_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "clauses"
        ).first()
        assert clause_analysis is not None
        assert isinstance(clause_analysis.result_json, dict)
        assert "payment_terms" in clause_analysis.result_json
    finally:
        db.close()
        cleanup_db()
