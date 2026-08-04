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
from app.models.user_session import UserSession
from app.core.security import create_access_token
from app.agents.qa_agent import answer_question_node, build_qa_graph, _clean_and_parse_json, QAState

client = TestClient(app)
TEST_EMAIL = "qa_test_user@example.com"

MOCK_QA_RESPONSE = """
{
  "answer": "This agreement can be terminated by either party for convenience upon giving thirty (30) days prior written notice to the other party (referencing Chunk 1).",
  "not_found": false
}
"""

MOCK_QA_NOT_FOUND_RESPONSE = """
{
  "answer": "",
  "not_found": true
}
"""

MOCK_RETRIEVED_CHUNKS = [
    {
        "id": "contract_1_chunk_1",
        "text": "Either party may terminate this Agreement for convenience by providing thirty (30) days written notice to the other party.",
        "chunk_index": 1,
        "contract_id": 1,
        "similarity": 0.85
    },
    {
        "id": "contract_1_chunk_2",
        "text": "This agreement shall be governed by and construed in accordance with the laws of India.",
        "chunk_index": 2,
        "contract_id": 1,
        "similarity": 0.50
    }
]

def cleanup_db():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
            for c in contracts:
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
            refresh_token_hash="qa-session-hash-123",
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
            filename="test_qa_agreement.pdf",
            upload_path="uploads/test_qa_agreement.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return f"Bearer {token}", contract.id, user.id
    finally:
        db.close()

def test_clean_and_parse_json_valid_qa():
    parsed = _clean_and_parse_json(MOCK_QA_RESPONSE)
    assert "answer" in parsed
    assert parsed["not_found"] is False
    assert "terminated" in parsed["answer"]

def test_clean_and_parse_json_not_found():
    parsed = _clean_and_parse_json(MOCK_QA_NOT_FOUND_RESPONSE)
    assert parsed["not_found"] is True

@patch("app.agents.qa_agent.get_vector_store_service")
@patch("app.agents.qa_agent.get_llm_response")
def test_qa_agent_node_answering(mock_get_llm, mock_get_vs):
    mock_get_llm.return_value = MOCK_QA_RESPONSE
    
    mock_vs_instance = mock_get_vs.return_value
    mock_vs_instance.query_contract_chunks.return_value = MOCK_RETRIEVED_CHUNKS
    
    initial_state: QAState = {
        "contract_id": 9999,
        "question": "How can I terminate this agreement?",
        "answer": "",
        "sources": [],
        "error": None
    }
    
    result = answer_question_node(initial_state)
    assert "answer" in result
    assert "sources" in result
    assert len(result["sources"]) == 2
    assert "thirty (30) days" in result["answer"]
    assert result["sources"][0]["chunk_index"] == 1

@patch("app.agents.qa_agent.get_vector_store_service")
@patch("app.agents.qa_agent.get_llm_response")
def test_qa_agent_graph_execution(mock_get_llm, mock_get_vs):
    mock_get_llm.return_value = MOCK_QA_RESPONSE
    mock_vs_instance = mock_get_vs.return_value
    mock_vs_instance.query_contract_chunks.return_value = MOCK_RETRIEVED_CHUNKS
    
    graph = build_qa_graph()
    initial_state: QAState = {
        "contract_id": 9999,
        "question": "How can I terminate this agreement?",
        "answer": "",
        "sources": [],
        "error": None
    }
    
    final_state = graph.invoke(initial_state)
    assert final_state["answer"] is not None
    assert len(final_state["sources"]) == 2
    assert final_state["error"] is None

@patch("app.agents.qa_agent.get_vector_store_service")
@patch("app.agents.qa_agent.get_llm_response")
def test_run_qa_agent_endpoint(mock_get_llm, mock_get_vs):
    mock_get_llm.return_value = MOCK_QA_RESPONSE
    
    mock_vs_instance = mock_get_vs.return_value
    mock_vs_instance.query_contract_chunks.return_value = MOCK_RETRIEVED_CHUNKS
    
    auth_header, contract_id, user_id = setup_test_environment()
    
    try:
        headers = {"Authorization": auth_header}
        payload = {"question": "How can I terminate this agreement?"}
        
        response = client.post(f"/contracts/{contract_id}/ask", json=payload, headers=headers)
        assert response.status_code == 200, f"Endpoint failed: {response.text}"
        
        data = response.json()
        assert data["contract_id"] == contract_id
        assert "answer" in data
        assert len(data["sources"]) == 2
        assert data["sources"][0]["chunk_index"] == 1
        assert "thirty (30) days" in data["answer"]
    finally:
        cleanup_db()
