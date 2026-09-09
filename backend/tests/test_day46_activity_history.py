"""
Day 46 Test Suite — Activity History Backend
---------------------------------------------
Verifies:
1. Audit logger service (safe logging, fail-open resilience, client telemetry extraction, multi-tenant querying)
2. Conversation lifecycle service (creation, turn persistence, cited sources tracking, title generation, cascading deletion)
3. API endpoints:
   - GET /history (paginated & filtered timeline)
   - GET /conversations (thread listings with message counts)
   - GET /conversations/{id} (full transcript with citations & tenant isolation)
   - PATCH /conversations/{id} (title renaming)
   - DELETE /conversations/{id} (deletion & cascading)
   - POST /contracts/{contract_id}/ask (conversation persistence & QA_MESSAGE_SENT audit log)
   - Contract viewing audit log (CONTRACT_VIEWED)

Day 46 — Activity History Backend
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, SessionLocal, get_db
from app.core.audit_events import AuditEventType, get_event_category, format_event_description
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User
from app.models.contract import Contract
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, ConversationMessage
from app.models.user_session import UserSession
from app.services.audit_logger import extract_client_info, log_activity, get_user_activity
from app.services.conversation_service import (
    generate_conversation_title,
    get_or_create_conversation,
    save_conversation_turn,
    list_user_conversations,
    get_conversation_detail,
    update_conversation_title,
    delete_conversation,
)

client = TestClient(app)

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture(scope="function")
def sqlite_session():
    """In-memory SQLite session for isolated ORM service unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


# ===========================================================================
# 1. Audit Logger Service Unit Tests
# ===========================================================================

def test_extract_client_info():
    """Verify IP and user agent extraction including X-Forwarded-For and truncation."""
    # None request
    ip, ua = extract_client_info(None)
    assert ip is None
    assert ua is None

    # Request with X-Forwarded-For
    mock_req = MagicMock()
    mock_req.headers = {
        "x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178",
        "user-agent": "Mozilla/5.0 TestBrowser",
    }
    ip, ua = extract_client_info(mock_req)
    assert ip == "203.0.113.195"
    assert ua == "Mozilla/5.0 TestBrowser"

    # Truncate user agent exceeding 255 chars
    long_ua = "A" * 300
    mock_req.headers = {"user-agent": long_ua}
    mock_req.client.host = "10.0.0.1"
    ip, ua = extract_client_info(mock_req)
    assert ip == "10.0.0.1"
    assert len(ua) == 255
    assert ua.endswith("...")


def test_log_activity_persistence_and_fields(sqlite_session):
    """Verify log_activity writes entry with status, IP, UA, metadata, and timestamps."""
    user = User(email="test_audit@legalai.com", hashed_password="pw", is_active=True)
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)

    entry = log_activity(
        db=sqlite_session,
        action=AuditEventType.CONTRACT_UPLOADED.value,
        user_id=user.id,
        resource_id=10,
        status="SUCCESS",
        metadata={"filename": "NDA.pdf", "size_bytes": 2048},
        ip_address="192.168.1.50",
        user_agent="TestAgent/1.0",
    )

    assert entry is not None
    assert entry.id is not None
    assert entry.action == "CONTRACT_UPLOADED"
    assert entry.user_id == user.id
    assert entry.resource_id == 10
    assert entry.status == "SUCCESS"
    assert entry.ip_address == "192.168.1.50"
    assert entry.user_agent == "TestAgent/1.0"
    assert entry.metadata_json["filename"] == "NDA.pdf"
    assert entry.timestamp is not None


def test_log_activity_fail_open(sqlite_session):
    """Verify log_activity does not raise exception if database operation fails."""
    # Create mock session that raises error on add/commit
    bad_session = MagicMock()
    bad_session.add.side_effect = RuntimeError("Database disk full")

    # Must fail open (return None, not raise exception)
    result = log_activity(
        db=bad_session,
        action=AuditEventType.USER_LOGIN.value,
        user_id=1,
    )
    assert result is None
    bad_session.rollback.assert_called_once()


def test_get_user_activity_multi_tenant_and_filtering(sqlite_session):
    """Verify get_user_activity isolates tenants and respects category, action, and date filters."""
    user1 = User(email="u1@test.com", hashed_password="pw", is_active=True)
    user2 = User(email="u2@test.com", hashed_password="pw", is_active=True)
    sqlite_session.add_all([user1, user2])
    sqlite_session.commit()
    sqlite_session.refresh(user1)
    sqlite_session.refresh(user2)

    # Insert test activities for user 1 and user 2
    log_activity(sqlite_session, action=AuditEventType.USER_LOGIN.value, user_id=user1.id, status="SUCCESS")
    log_activity(sqlite_session, action=AuditEventType.CONTRACT_UPLOADED.value, user_id=user1.id, status="SUCCESS", metadata={"filename": "doc1.pdf"})
    log_activity(sqlite_session, action=AuditEventType.SEARCH_PERFORMED.value, user_id=user1.id, status="SUCCESS", metadata={"query": "confidentiality"})
    log_activity(sqlite_session, action=AuditEventType.USER_LOGIN_FAILED.value, user_id=user1.id, status="FAILURE")

    # User 2 activity (must never be returned for user 1)
    log_activity(sqlite_session, action=AuditEventType.USER_LOGIN.value, user_id=user2.id, status="SUCCESS")

    # 1. Total for user 1
    items, total = get_user_activity(sqlite_session, user_id=user1.id)
    assert total == 4
    assert len(items) == 4
    # Ensure enriched fields
    assert items[0].category in ["AUTH", "CONTRACTS", "SEARCH"]
    assert items[0].description != ""

    # 2. Category filter: AUTH
    auth_items, auth_total = get_user_activity(sqlite_session, user_id=user1.id, category="AUTH")
    assert auth_total == 2
    for it in auth_items:
        assert it.action in [AuditEventType.USER_LOGIN.value, AuditEventType.USER_LOGIN_FAILED.value]

    # 3. Status filter: FAILURE
    fail_items, fail_total = get_user_activity(sqlite_session, user_id=user1.id, status="FAILURE")
    assert fail_total == 1
    assert fail_items[0].action == AuditEventType.USER_LOGIN_FAILED.value

    # 4. Action filter: SEARCH_PERFORMED
    search_items, search_total = get_user_activity(sqlite_session, user_id=user1.id, action=AuditEventType.SEARCH_PERFORMED.value)
    assert search_total == 1
    assert "confidentiality" in search_items[0].description

    # 5. User 2 has only 1 entry
    u2_items, u2_total = get_user_activity(sqlite_session, user_id=user2.id)
    assert u2_total == 1
    assert u2_items[0].user_id == user2.id


# ===========================================================================
# 2. Conversation Service Unit Tests
# ===========================================================================

def test_conversation_title_generator():
    """Verify title generation truncates gracefully."""
    short = "What is the termination period?"
    assert generate_conversation_title(short) == "What is the termination period?"

    long_q = "Can the vendor terminate this master services agreement immediately if the client fails to make payment within forty-five business days of invoice submission?"
    title = generate_conversation_title(long_q)
    assert len(title) <= 60
    assert title.endswith("...")


def test_conversation_lifecycle(sqlite_session):
    """Verify get_or_create, turn persistence, citations, title update, and deletion."""
    user = User(email="lawyer@firm.com", hashed_password="pw", is_active=True)
    sqlite_session.add(user)
    sqlite_session.commit()

    contract = Contract(user_id=user.id, filename="SaaS_Agreement.pdf", upload_path="/tmp/saas.pdf", status="analyzed")
    sqlite_session.add(contract)
    sqlite_session.commit()

    # 1. Create initial conversation
    convo = get_or_create_conversation(sqlite_session, user_id=user.id, contract_id=contract.id)
    assert convo.id is not None
    assert convo.title == "New Conversation"

    # 2. Save dialogue turn with citations
    sources = [{"chunk_index": 0, "text": "Net 30 payment terms", "similarity": 0.88}]
    user_msg, asst_msg = save_conversation_turn(
        db=sqlite_session,
        conversation=convo,
        question="What are the payment terms?",
        answer="Invoices are payable within 30 days.",
        sources=sources,
    )
    assert user_msg.role == "user"
    assert asst_msg.role == "assistant"
    assert asst_msg.cited_clause_refs == sources
    # Title should auto-update from "New Conversation" to the question
    assert convo.title == "What are the payment terms?"

    # 3. List conversations
    convos = list_user_conversations(sqlite_session, user_id=user.id)
    assert len(convos) == 1
    assert convos[0].id == convo.id
    assert convos[0].message_count == 2
    assert convos[0].contract_filename == "SaaS_Agreement.pdf"

    # 4. Get conversation detail
    detail = get_conversation_detail(sqlite_session, user_id=user.id, conversation_id=convo.id)
    assert detail is not None
    assert len(detail.messages) == 2
    assert detail.messages[1].cited_clause_refs[0]["text"] == "Net 30 payment terms"

    # 5. Update title
    updated = update_conversation_title(sqlite_session, user_id=user.id, conversation_id=convo.id, new_title="Payment & Billing Terms")
    assert updated.title == "Payment & Billing Terms"

    # 6. Delete conversation
    success = delete_conversation(sqlite_session, user_id=user.id, conversation_id=convo.id)
    assert success is True
    assert get_conversation_detail(sqlite_session, user_id=user.id, conversation_id=convo.id) is None


# ===========================================================================
# 3. Live API Integration Tests (via TestClient & PostgreSQL)
# ===========================================================================

TEST_USER_A = "day46_usera@legalai.com"
TEST_USER_B = "day46_userb@legalai.com"


@pytest.fixture(scope="module")
def setup_api_users():
    """Sets up two test users with valid sessions in the database."""
    db = SessionLocal()
    try:
        # Cleanup any existing test users
        for email in [TEST_USER_A, TEST_USER_B]:
            u = db.query(User).filter_by(email=email).first()
            if u:
                db.query(Conversation).filter_by(user_id=u.id).delete()
                db.query(AuditLog).filter_by(user_id=u.id).delete()
                db.query(UserSession).filter_by(user_id=u.id).delete()
                db.query(Contract).filter_by(user_id=u.id).delete()
                db.delete(u)
        db.commit()

        # Create user A
        user_a = User(email=TEST_USER_A, hashed_password=hash_password("Pass123!"), is_active=True)
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

        # Create user B
        user_b = User(email=TEST_USER_B, hashed_password=hash_password("Pass123!"), is_active=True)
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

        # Create contracts for User A
        contract_a = Contract(
            user_id=user_a.id,
            filename="Enterprise_Master_Agreement.pdf",
            upload_path="/tmp/ema.pdf",
            status="analyzed",
        )
        db.add(contract_a)
        db.commit()
        db.refresh(contract_a)

        # Active session and token for User A
        _, session_a_id = create_refresh_token(user_id=user_a.id, db=db)
        token_a = create_access_token({"sub": user_a.email, "session_id": session_a_id})

        # Active session and token for User B
        _, session_b_id = create_refresh_token(user_id=user_b.id, db=db)
        token_b = create_access_token({"sub": user_b.email, "session_id": session_b_id})

        yield {
            "user_a_id": user_a.id,
            "token_a": token_a,
            "contract_a_id": contract_a.id,
            "user_b_id": user_b.id,
            "token_b": token_b,
        }
    finally:
        # Final cleanup
        for email in [TEST_USER_A, TEST_USER_B]:
            u = db.query(User).filter_by(email=email).first()
            if u:
                db.query(Conversation).filter_by(user_id=u.id).delete()
                db.query(AuditLog).filter_by(user_id=u.id).delete()
                db.query(UserSession).filter_by(user_id=u.id).delete()
                db.query(Contract).filter_by(user_id=u.id).delete()
                db.delete(u)
        db.commit()
        db.close()


def test_api_history_feed(setup_api_users):
    """Verify GET /history returns paginated, category-enriched user activity feed."""
    token_a = setup_api_users["token_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    # Generate some logged activities
    db = SessionLocal()
    try:
        log_activity(db, action=AuditEventType.USER_LOGIN.value, user_id=setup_api_users["user_a_id"])
        log_activity(db, action=AuditEventType.CONTRACT_UPLOADED.value, user_id=setup_api_users["user_a_id"], metadata={"filename": "Test.pdf"})
    finally:
        db.close()

    # 1. Unauthenticated request should fail
    unauth_resp = client.get("/history")
    assert unauth_resp.status_code == 401

    # 2. Authenticated request
    resp = client.get("/history?limit=10&offset=0", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    first_item = data["items"][0]
    assert "category" in first_item
    assert "description" in first_item
    assert first_item["user_id"] == setup_api_users["user_a_id"]

    # 3. Filter by category
    cat_resp = client.get("/history?category=AUTH", headers=headers)
    assert cat_resp.status_code == 200
    for it in cat_resp.json()["items"]:
        assert it["category"] == "AUTH"


@patch("app.agents.qa_agent.get_vector_store_service")
@patch("app.agents.qa_agent.get_llm_response")
def test_api_qa_and_conversation_persistence(mock_llm, mock_vs, setup_api_users):
    """Verify POST /contracts/{id}/ask creates conversation thread and persists turns with citations."""
    mock_llm.return_value = '{"answer": "Notice period is 60 calendar days.", "not_found": false}'
    mock_vs_inst = mock_vs.return_value
    mock_vs_inst.query_contract_chunks.return_value = [
        {"chunk_index": 2, "text": "Section 14: 60 days written notice.", "similarity": 0.94}
    ]

    token_a = setup_api_users["token_a"]
    contract_id = setup_api_users["contract_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    # 1. Ask question (starts a conversation)
    payload = {"question": "What is the required notice period for termination?"}
    ask_resp = client.post(f"/contracts/{contract_id}/ask", json=payload, headers=headers)
    assert ask_resp.status_code == 200
    data = ask_resp.json()
    assert "conversation_id" in data
    convo_id = data["conversation_id"]
    assert data["answer"] == "Notice period is 60 calendar days."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["chunk_index"] == 2

    # 2. Verify conversation listed in GET /conversations
    list_resp = client.get("/conversations", headers=headers)
    assert list_resp.status_code == 200
    convos = list_resp.json()
    matching = [c for c in convos if c["id"] == convo_id]
    assert len(matching) == 1
    assert matching[0]["contract_id"] == contract_id
    assert matching[0]["contract_filename"] == "Enterprise_Master_Agreement.pdf"
    assert matching[0]["message_count"] == 2

    # 3. Verify conversation detail in GET /conversations/{id}
    detail_resp = client.get(f"/conversations/{convo_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][0]["content"] == payload["question"]
    assert detail["messages"][1]["role"] == "assistant"
    assert detail["messages"][1]["cited_clause_refs"][0]["similarity"] == 0.94

    # 4. Ask follow-up question on same conversation
    payload_followup = {
        "question": "Can notice be provided by electronic mail?",
        "conversation_id": convo_id,
    }
    followup_resp = client.post(f"/contracts/{contract_id}/ask", json=payload_followup, headers=headers)
    assert followup_resp.status_code == 200
    assert followup_resp.json()["conversation_id"] == convo_id

    # 5. Detail should now have 4 messages
    detail_resp2 = client.get(f"/conversations/{convo_id}", headers=headers)
    assert len(detail_resp2.json()["messages"]) == 4

    # 6. Verify audit log has QA_MESSAGE_SENT
    db = SessionLocal()
    try:
        log_entry = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == setup_api_users["user_a_id"], AuditLog.action == AuditEventType.QA_MESSAGE_SENT.value)
            .first()
        )
        assert log_entry is not None
        assert log_entry.resource_id == contract_id
    finally:
        db.close()


def test_api_conversation_security_and_management(setup_api_users):
    """Verify tenant isolation on conversation detail, title updates, and deletion."""
    token_a = setup_api_users["token_a"]
    token_b = setup_api_users["token_b"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Fetch User A's conversation ID
    list_resp = client.get("/conversations", headers=headers_a)
    assert list_resp.status_code == 200
    user_a_convos = list_resp.json()
    assert len(user_a_convos) > 0
    convo_id = user_a_convos[0]["id"]

    # 1. User B should NOT be able to view User A's conversation (returns 404)
    forbidden_get = client.get(f"/conversations/{convo_id}", headers=headers_b)
    assert forbidden_get.status_code == 404

    # 2. User B should NOT be able to update User A's conversation title (returns 404)
    forbidden_patch = client.patch(
        f"/conversations/{convo_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert forbidden_patch.status_code == 404

    # 3. User B should NOT be able to delete User A's conversation (returns 404)
    forbidden_delete = client.delete(f"/conversations/{convo_id}", headers=headers_b)
    assert forbidden_delete.status_code == 404

    # 4. User A updates their conversation title
    update_resp = client.patch(
        f"/conversations/{convo_id}",
        json={"title": "Custom Renamed Thread"},
        headers=headers_a,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Custom Renamed Thread"

    # 5. User A deletes their conversation
    del_resp = client.delete(f"/conversations/{convo_id}", headers=headers_a)
    assert del_resp.status_code == 200

    # 6. Conversation is now gone
    not_found_resp = client.get(f"/conversations/{convo_id}", headers=headers_a)
    assert not_found_resp.status_code == 404


def test_retrofitted_contract_view_audit_log(setup_api_users):
    """Verify GET /contracts/{id} records a CONTRACT_VIEWED audit entry."""
    token_a = setup_api_users["token_a"]
    contract_id = setup_api_users["contract_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    resp = client.get(f"/contracts/{contract_id}", headers=headers)
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        view_log = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == setup_api_users["user_a_id"],
                AuditLog.action == AuditEventType.CONTRACT_VIEWED.value,
                AuditLog.resource_id == contract_id,
            )
            .first()
        )
        assert view_log is not None
        assert view_log.status == "SUCCESS"
        assert view_log.metadata_json["filename"] == "Enterprise_Master_Agreement.pdf"
    finally:
        db.close()
