"""
Day 48 Test Suite — History Privacy, Retention, and Data Export
--------------------------------------------------------------
Verifies:
1. Multi-Tenant Privacy Isolation:
   - Strict user scoping across history, conversations, export, and retention.
   - Cross-user data snooping or mutation attempts fail with 404 or empty sets.
2. Full Account Data Portability:
   - GET /account/export generates complete, downloadable JSON archive with contracts,
     analyses, conversations with citations, and activity audit logs.
3. User-Configurable Data Retention:
   - GET /account/retention and PATCH /account/retention.
   - Input validation (30, 90, 180, 365, null).
   - Automatic retroactive log purging for records exceeding retention threshold.
   - DATA_RETENTION_UPDATED audit logging.
4. Verified Multi-Step Cascade Account Deletion:
   - POST /account/delete-otp dispatches security verification code.
   - DELETE /account enforces dual verification (password + fresh Email OTP).
   - Cascades deletion across contracts, analyses, conversations, messages, sessions.
   - Preserves compliance audit logs with user_id = NULL.
   - Physical file and ChromaDB cleanup.

Day 48 — History Privacy, Retention, and Data Export
"""

import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, SessionLocal
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.core.audit_events import AuditEventType
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit_log import AuditLog
from app.models.email_otp import EmailOTPVerification
from app.models.user_session import UserSession
from app.services.audit_logger import log_activity
from app.services.otp_service import hash_token
from app.services import account_service

client = TestClient(app)

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


TEST_USER_A = "alice_privacy@test.com"
TEST_USER_B = "bob_privacy@test.com"
TEST_PASSWORD = "StrongSecurePassword123!"


@pytest.fixture(scope="function")
def setup_privacy_users():
    """Sets up two isolated test users with contracts, conversations, and audit logs."""
    db = SessionLocal()
    try:
        # Cleanup any pre-existing test users
        for email in [TEST_USER_A, TEST_USER_B]:
            u = db.query(User).filter_by(email=email).first()
            if u:
                db.query(Conversation).filter_by(user_id=u.id).delete()
                db.query(AuditLog).filter_by(user_id=u.id).delete()
                db.query(UserSession).filter_by(user_id=u.id).delete()
                db.query(Contract).filter_by(user_id=u.id).delete()
                db.delete(u)
        db.commit()

        # Create Alice
        user_a = User(
            email=TEST_USER_A,
            hashed_password=hash_password(TEST_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(user_a)

        # Create Bob
        user_b = User(
            email=TEST_USER_B,
            hashed_password=hash_password(TEST_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        # Create contract for Alice
        contract_a = Contract(
            filename="Alice_Confidential_NDA.pdf",
            upload_path="/tmp/alice_test_nda.pdf",
            status="analyzed",
            user_id=user_a.id,
        )
        db.add(contract_a)
        db.commit()
        db.refresh(contract_a)

        # Create analysis for Alice's contract
        analysis_a = Analysis(
            contract_id=contract_a.id,
            analysis_type="summary",
            result_json={"summary": "Alice confidential trade secret agreement."},
        )
        db.add(analysis_a)

        # Create conversation for Alice
        convo_a = Conversation(
            user_id=user_a.id,
            contract_id=contract_a.id,
            title="Alice Confidential Discussion",
            last_message_at=datetime.now(timezone.utc),
        )
        db.add(convo_a)
        db.commit()
        db.refresh(convo_a)

        # Add message to Alice's conversation
        msg_a = ConversationMessage(
            conversation_id=convo_a.id,
            role="user",
            content="What are my non-compete liabilities?",
        )
        msg_ai = ConversationMessage(
            conversation_id=convo_a.id,
            role="assistant",
            content="Section 4 prohibits solicitation for 24 months.",
            cited_clause_refs=[{"chunk_index": 1, "text": "Non-solicitation 24 months.", "similarity": 0.95}],
        )
        db.add_all([msg_a, msg_ai])

        # Add audit logs for Alice
        log_activity(db, action=AuditEventType.USER_LOGIN.value, user_id=user_a.id)
        log_activity(db, action=AuditEventType.CONTRACT_UPLOADED.value, user_id=user_a.id, metadata={"filename": contract_a.filename})

        # Add audit log for Bob
        log_activity(db, action=AuditEventType.USER_LOGIN.value, user_id=user_b.id)

        # Active sessions for Alice and Bob
        _, session_a_id = create_refresh_token(user_id=user_a.id, db=db)
        token_a = create_access_token(data={"sub": user_a.email, "session_id": session_a_id})

        _, session_b_id = create_refresh_token(user_id=user_b.id, db=db)
        token_b = create_access_token(data={"sub": user_b.email, "session_id": session_b_id})

        yield {
            "user_a_id": user_a.id,
            "user_a_email": user_a.email,
            "user_b_id": user_b.id,
            "user_b_email": user_b.email,
            "token_a": token_a,
            "token_b": token_b,
            "contract_a_id": contract_a.id,
            "convo_a_id": convo_a.id,
        }
    finally:
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


# ===========================================================================
# 1. Multi-Tenant Privacy Isolation Tests
# ===========================================================================

def test_multi_tenant_history_privacy_isolation(setup_privacy_users):
    """
    Verify absolute isolation: Bob can never see, access, mutate, or export Alice's
    history, conversations, or contracts.
    """
    token_b = setup_privacy_users["token_b"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    convo_a_id = setup_privacy_users["convo_a_id"]

    # 1. Bob's GET /history contains only Bob's actions, never Alice's
    resp_history = client.get("/history", headers=headers_b)
    assert resp_history.status_code == 200
    b_items = resp_history.json()["items"]
    for item in b_items:
        assert item["user_id"] == setup_privacy_users["user_b_id"]
        assert "Alice_Confidential_NDA.pdf" not in str(item)

    # 2. Bob's GET /conversations does not list Alice's conversation
    resp_convos = client.get("/conversations", headers=headers_b)
    assert resp_convos.status_code == 200
    b_convos = resp_convos.json()
    assert len(b_convos) == 0

    # 3. Bob directly requesting Alice's conversation detail returns 404
    resp_detail = client.get(f"/conversations/{convo_a_id}", headers=headers_b)
    assert resp_detail.status_code == 404

    # 4. Bob attempting to rename Alice's conversation returns 404
    resp_patch = client.patch(f"/conversations/{convo_a_id}", json={"title": "Hacked"}, headers=headers_b)
    assert resp_patch.status_code == 404

    # 5. Bob attempting to delete Alice's conversation returns 404
    resp_del = client.delete(f"/conversations/{convo_a_id}", headers=headers_b)
    assert resp_del.status_code == 404


# ===========================================================================
# 2. Full Account Data Export Tests
# ===========================================================================

def test_account_export_structure_and_completeness(setup_privacy_users):
    """Verify GET /account/export streams a comprehensive, complete JSON compliance export."""
    token_a = setup_privacy_users["token_a"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Request data export
    resp = client.get("/account/export", headers=headers_a)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    assert "attachment; filename=\"legal_intel_export_user_" in resp.headers["content-disposition"]

    data = resp.json()

    # 2. Verify Export Metadata
    assert "export_metadata" in data
    assert data["export_metadata"]["user_id"] == setup_privacy_users["user_a_id"]
    assert data["export_metadata"]["user_email"] == TEST_USER_A
    assert data["export_metadata"]["platform"] == "AI Legal Document Intelligence Platform"

    # 3. Verify Account Profile
    assert "account_profile" in data
    assert data["account_profile"]["email"] == TEST_USER_A

    # 4. Verify Contracts with Analyses
    assert "contracts" in data
    assert len(data["contracts"]) == 1
    contract = data["contracts"][0]
    assert contract["filename"] == "Alice_Confidential_NDA.pdf"
    assert len(contract["analyses"]) == 1
    assert contract["analyses"][0]["analysis_type"] == "summary"

    # 5. Verify Conversations with Messages and Citations
    assert "conversations" in data
    assert len(data["conversations"]) == 1
    convo = data["conversations"][0]
    assert convo["title"] == "Alice Confidential Discussion"
    assert convo["message_count"] == 2
    assert len(convo["messages"]) == 2
    assistant_msg = convo["messages"][1]
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["cited_clause_refs"]) == 1
    assert assistant_msg["cited_clause_refs"][0]["similarity"] == 0.95

    # 6. Verify Activity History
    assert "activity_history" in data
    assert len(data["activity_history"]) >= 2
    actions = [log["action"] for log in data["activity_history"]]
    assert AuditEventType.USER_LOGIN.value in actions
    assert AuditEventType.CONTRACT_UPLOADED.value in actions

    # 7. Verify DATA_EXPORTED audit event was logged
    db = SessionLocal()
    try:
        export_log = (
            db.query(AuditLog)
            .filter_by(user_id=setup_privacy_users["user_a_id"], action=AuditEventType.DATA_EXPORTED.value)
            .first()
        )
        assert export_log is not None
        assert export_log.status == "SUCCESS"
    finally:
        db.close()


# ===========================================================================
# 3. Data Retention Policy Tests
# ===========================================================================

def test_data_retention_policy_flow(setup_privacy_users):
    """Verify getting, updating, validating, and applying retention policies."""
    token_a = setup_privacy_users["token_a"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    user_a_id = setup_privacy_users["user_a_id"]

    # 1. Initial retention policy is indefinite (None)
    get_resp = client.get("/account/retention", headers=headers_a)
    assert get_resp.status_code == 200
    assert get_resp.json()["data_retention_days"] is None

    # 2. Validation: invalid days returns 422
    inv_resp = client.patch("/account/retention", json={"data_retention_days": 45}, headers=headers_a)
    assert inv_resp.status_code == 422

    # 3. Add an old audit log (120 days ago) and a recent audit log (5 days ago)
    db = SessionLocal()
    try:
        old_log = AuditLog(
            user_id=user_a_id,
            action=AuditEventType.SEARCH_PERFORMED.value,
            status="SUCCESS",
            timestamp=datetime.now(timezone.utc) - timedelta(days=120),
        )
        recent_log = AuditLog(
            user_id=user_a_id,
            action=AuditEventType.SEARCH_PERFORMED.value,
            status="SUCCESS",
            timestamp=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db.add_all([old_log, recent_log])
        db.commit()
        old_log_id = old_log.id
        recent_log_id = recent_log.id
    finally:
        db.close()

    # 4. Set retention policy to 90 days -> should retroactively purge the 120-day log
    patch_resp = client.patch("/account/retention", json={"data_retention_days": 90}, headers=headers_a)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data_retention_days"] == 90
    assert "Retention policy updated to 90 days" in patch_resp.json()["message"]

    # 5. Verify database state: old log is gone, recent log is preserved
    db = SessionLocal()
    try:
        assert db.query(AuditLog).filter_by(id=old_log_id).first() is None
        assert db.query(AuditLog).filter_by(id=recent_log_id).first() is not None

        # Verify DATA_RETENTION_UPDATED audit log was recorded
        retention_log = (
            db.query(AuditLog)
            .filter_by(user_id=user_a_id, action=AuditEventType.DATA_RETENTION_UPDATED.value)
            .first()
        )
        assert retention_log is not None
        assert retention_log.metadata_json["data_retention_days"] == 90
    finally:
        db.close()


# ===========================================================================
# 4. Account Deletion Tests
# ===========================================================================

@patch("app.services.account_service.get_vector_store_service")
def test_account_deletion_verification_and_cascade(mock_vs, setup_privacy_users):
    """
    Verify complete account deletion:
    - Step 1: Request OTP
    - Step 2: Delete account with password + OTP validation
    - Step 3: Cascading entity deletion, file deletion, ChromaDB cleanup
    - Step 4: Audit log preservation with user_id = NULL
    """
    mock_vs_inst = MagicMock()
    mock_vs.return_value = mock_vs_inst

    # Create a disposable user dedicated to deletion
    db = SessionLocal()
    try:
        existing_del = db.query(User).filter_by(email="delete_target@legalai.com").first()
        if existing_del:
            db.query(Conversation).filter_by(user_id=existing_del.id).delete()
            db.query(AuditLog).filter_by(user_id=existing_del.id).delete()
            db.query(UserSession).filter_by(user_id=existing_del.id).delete()
            db.query(Contract).filter_by(user_id=existing_del.id).delete()
            db.delete(existing_del)
            db.commit()

        del_user = User(
            email="delete_target@legalai.com",
            hashed_password=hash_password("DeletePass123!"),
            is_active=True,
        )
        db.add(del_user)
        db.commit()
        db.refresh(del_user)

        # Add contract with dummy file
        dummy_file = "/tmp/test_delete_target.pdf"
        with open(dummy_file, "w") as f:
            f.write("Dummy PDF content")

        contract = Contract(
            filename="target.pdf",
            upload_path=dummy_file,
            status="analyzed",
            user_id=del_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Add conversation
        convo = Conversation(
            user_id=del_user.id,
            contract_id=contract.id,
            title="Target Conversation",
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

        del_user_id = del_user.id
        contract_id = contract.id
        _, session_del_id = create_refresh_token(user_id=del_user.id, db=db)
        del_token = create_access_token(data={"sub": del_user.email, "session_id": session_del_id})
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {del_token}"}

    # 1. Request deletion OTP
    otp_resp = client.post("/account/delete-otp", headers=headers)
    assert otp_resp.status_code == 200
    assert "Deletion confirmation code dispatched" in otp_resp.json()["message"]

    # Retrieve dispatched OTP from DB
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter_by(email="delete_target@legalai.com").first()
        assert otp_entry is not None
    finally:
        db.close()

    # 2. Attempt deletion with wrong password -> 401
    fail_pw_resp = client.request(
        "DELETE",
        "/account",
        json={"password": "WrongPassword!", "otp_code": "123456"},
        headers=headers,
    )
    assert fail_pw_resp.status_code == 401

    # 3. Attempt deletion with wrong OTP -> 400
    fail_otp_resp = client.request(
        "DELETE",
        "/account",
        json={"password": "DeletePass123!", "otp_code": "000000"},
        headers=headers,
    )
    assert fail_otp_resp.status_code == 400

    # 4. Set a known OTP in the database for deterministic verification
    test_otp = "889900"
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter_by(email="delete_target@legalai.com").first()
        otp_entry.otp_hash = hash_token(test_otp)
        otp_entry.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        otp_entry.attempts = 0
        db.commit()
    finally:
        db.close()

    # 5. Execute deletion with valid credentials and valid OTP
    del_resp = client.request(
        "DELETE",
        "/account",
        json={"password": "DeletePass123!", "otp_code": test_otp},
        headers=headers,
    )
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["deleted_contracts_count"] == 1
    assert del_data["deleted_conversations_count"] == 1

    # 6. Verify User record is permanently gone
    db = SessionLocal()
    try:
        assert db.query(User).filter_by(id=del_user_id).first() is None
        assert db.query(Contract).filter_by(id=contract_id).first() is None
        assert db.query(Conversation).filter_by(user_id=del_user_id).first() is None

        # Verify audit logs preserved with user_id = NULL
        del_log = (
            db.query(AuditLog)
            .filter_by(action=AuditEventType.ACCOUNT_DELETED.value)
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert del_log is not None
        assert del_log.user_id is None
        assert del_log.metadata_json["deleted_user_email"] == "delete_target@legalai.com"
    finally:
        db.close()

    # 7. Verify local file and vector store cleanup were called
    assert not os.path.exists(dummy_file)
    mock_vs_inst.delete_contract_chunks.assert_called_with(contract_id)

    # 8. Subsequent API requests with old token return 401
    post_del_resp = client.get("/auth/me", headers=headers)
    assert post_del_resp.status_code == 401
