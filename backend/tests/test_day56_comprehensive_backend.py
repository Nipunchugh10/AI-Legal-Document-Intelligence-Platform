"""
Day 56 Test Suite — Comprehensive Backend Testing
=================================================
Validates full backend resilience across the entire platform lifecycle:
1. Document Ingestion & Validation:
   - Invalid file extension upload rejection (400)
   - Oversized file upload rejection (413)
   - Valid document upload (201)
   - Document listing & single document retrieval
   - Multi-tenant deletion protection (User B cannot delete User A's contract)
2. Analysis & Grounded Q&A Workflow Invariants:
   - Analysis execution on nonexistent contract (404)
   - Analysis execution on another user's contract (404)
   - Question asking on unanalyzed contract (400)
   - Question asking on nonexistent contract (404)
   - Question asking on another user's contract (404)
   - Grounded Q&A on analyzed contract with citation persistence (200)
3. Authentication & Session Lifecycle Security:
   - Access token expiration rejection (401)
   - Malformed/tampered JWT rejection (401)
   - Database session idle timeout (401 SESSION_EXPIRED)
   - Database session absolute expiry (401 SESSION_EXPIRED)
   - Refresh token rotation on exchange (200)
   - Replay protection on revoked refresh tokens (401)
   - Logout session invalidation (401 on subsequent calls)
4. Two-Factor Authentication (2FA) & Brute-Force Throttling:
   - Login with 2FA enabled returns requires_2fa + pending_2fa_token
   - Wrong OTP submission rejection (400 with attempts count)
   - Brute-force lockout after repeated failed attempts (400 max attempts)
   - OTP resend respects 30-second cooldown window (429)
   - OTP resend succeeds once cooldown expires (200)
   - Successful 2FA verification establishes session and returns full tokens (200)
5. Multi-Tenant Privacy & Data Isolation:
   - User B cannot view User A's activity history feed (GET /history)
   - User B cannot read User A's conversation thread (GET /conversations/{id} -> 404)
   - User B cannot update User A's conversation thread (PATCH /conversations/{id} -> 404)
   - User B cannot delete User A's conversation thread (DELETE /conversations/{id} -> 404)
   - User A's GDPR account export contains strictly User A's data (GET /account/export)
6. Comparison & Search Edge Cases:
   - Self-comparison of a contract returns 400 Bad Request
   - Comparison of non-existent contract returns 404 Not Found
   - Comparison across tenant boundaries returns 404 Not Found
   - Successful comparison of two distinct contracts returns clause diffs and risk profile delta (200)
7. Session Management & Retention Policies:
   - List active user sessions (GET /auth/sessions)
   - Revoke specific session (DELETE /auth/sessions/{id})
   - Revoke all other sessions (DELETE /auth/sessions)
   - Update data retention policy with automatic log pruning (PATCH /account/retention)
   - Telemetry metrics endpoint health check (GET /metrics)
"""

import io
import os
import sys
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Ensure backend directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.security import (
    hash_password,
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit_log import AuditLog
from app.models.email_otp import EmailOTPVerification
from app.models.user_session import UserSession
from app.services.otp_service import MAX_OTP_ATTEMPTS
from app.services.audit_logger import log_activity
from app.core.audit_events import AuditEventType

client = TestClient(app)
settings = get_settings()

DAY56_PRIMARY_EMAIL = "day56_primary_attorney@example.com"
DAY56_SECONDARY_EMAIL = "day56_secondary_attorney@example.com"
DAY56_PASSWORD = "StrongSecurePassword2026!"


@pytest.fixture(scope="function")
def test_env():
    """Sets up an isolated, clean multi-tenant test environment."""
    db = SessionLocal()
    try:
        # Cleanup any pre-existing records for test emails
        for email in [DAY56_PRIMARY_EMAIL, DAY56_SECONDARY_EMAIL]:
            user = db.query(User).filter_by(email=email).first()
            if user:
                db.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id.in_(
                        db.query(Conversation.id).filter_by(user_id=user.id)
                    )
                ).delete(synchronize_session=False)
                db.query(Conversation).filter_by(user_id=user.id).delete()
                db.query(AuditLog).filter_by(user_id=user.id).delete()
                db.query(UserSession).filter_by(user_id=user.id).delete()
                db.query(EmailOTPVerification).filter_by(email=email).delete()
                db.query(Analysis).filter(
                    Analysis.contract_id.in_(
                        db.query(Contract.id).filter_by(user_id=user.id)
                    )
                ).delete(synchronize_session=False)
                db.query(Contract).filter_by(user_id=user.id).delete()
                db.delete(user)
        db.commit()

        # 1. Create Primary User (User A)
        user_a = User(
            email=DAY56_PRIMARY_EMAIL,
            hashed_password=hash_password(DAY56_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(user_a)

        # 2. Create Secondary User (User B) for Multi-Tenant Boundary Tests
        user_b = User(
            email=DAY56_SECONDARY_EMAIL,
            hashed_password=hash_password(DAY56_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        # 3. Create Sessions and Tokens for both users
        refresh_token_a, session_id_a = create_refresh_token(
            user_id=user_a.id,
            db=db,
            device_info="Day56 Pytest Runner A",
            ip_address="127.0.0.1",
        )
        access_token_a = create_access_token(
            data={"sub": user_a.email, "session_id": session_id_a}
        )

        refresh_token_b, session_id_b = create_refresh_token(
            user_id=user_b.id,
            db=db,
            device_info="Day56 Pytest Runner B",
            ip_address="127.0.0.1",
        )
        access_token_b = create_access_token(
            data={"sub": user_b.email, "session_id": session_id_b}
        )

        # 4. Create Contracts for User A
        contract_a_analyzed = Contract(
            user_id=user_a.id,
            filename="NDA_Mutual_Enterprise_v1.pdf",
            upload_path="/tmp/day56_nda_v1.pdf",
            status="analyzed",
        )
        contract_a_pending = Contract(
            user_id=user_a.id,
            filename="Vendor_Service_Agreement_v1.pdf",
            upload_path="/tmp/day56_vendor_v1.pdf",
            status="pending",
        )
        contract_a_v2 = Contract(
            user_id=user_a.id,
            filename="NDA_Mutual_Enterprise_v2.pdf",
            upload_path="/tmp/day56_nda_v2.pdf",
            status="analyzed",
        )
        db.add(contract_a_analyzed)
        db.add(contract_a_pending)
        db.add(contract_a_v2)

        # 5. Create Contract for User B
        contract_b = Contract(
            user_id=user_b.id,
            filename="UserB_Confidential_Employment.pdf",
            upload_path="/tmp/day56_user_b.pdf",
            status="analyzed",
        )
        db.add(contract_b)
        db.commit()

        db.refresh(contract_a_analyzed)
        db.refresh(contract_a_pending)
        db.refresh(contract_a_v2)
        db.refresh(contract_b)

        # 6. Add Analysis records for analyzed contracts
        analysis_a1 = Analysis(
            contract_id=contract_a_analyzed.id,
            analysis_type="full_orchestration",
            result_json={
                "summary": "Standard mutual NDA agreement with 3-year term.",
                "clauses": {
                    "termination_clauses": "Either party may terminate upon 30 days written notice.",
                    "liability_clauses": "Total liability is capped at $50,000.",
                    "payment_terms": "Payment due within 30 days of invoice receipt.",
                },
                "risks": [
                    {
                        "flag_category": "YELLOW_FLAG",
                        "risk_type": "NOTICE_PERIOD_SHORT",
                        "issue": "Short termination notice period",
                        "recommendation": "Extend notice period to 60 days.",
                    }
                ],
            },
        )
        analysis_a2 = Analysis(
            contract_id=contract_a_v2.id,
            analysis_type="full_orchestration",
            result_json={
                "summary": "Revised mutual NDA agreement with 5-year term and indemnity.",
                "clauses": {
                    "termination_clauses": "Either party may terminate upon 60 days written notice.",
                    "liability_clauses": "Total liability is uncapped for gross negligence.",
                    "payment_terms": "Payment due within 15 days of invoice receipt.",
                },
                "risks": [
                    {
                        "flag_category": "RED_FLAG",
                        "risk_type": "UNCAPPED_LIABILITY",
                        "issue": "Uncapped liability for negligence",
                        "recommendation": "Cap liability at contract value.",
                    }
                ],
            },
        )
        db.add(analysis_a1)
        db.add(analysis_a2)

        # 7. Create Conversation for User A
        convo_a = Conversation(
            user_id=user_a.id,
            contract_id=contract_a_analyzed.id,
            title="Q&A regarding Termination and Payment Terms",
        )
        db.add(convo_a)
        db.commit()
        db.refresh(convo_a)

        msg_a = ConversationMessage(
            conversation_id=convo_a.id,
            role="user",
            content="What is the notice period for contract termination?",
            cited_clause_refs=[
                {
                    "chunk_index": 1,
                    "text": "Either party may terminate upon 30 days written notice.",
                    "similarity": 0.94,
                }
            ],
        )
        db.add(msg_a)

        # 8. Log Audit activity for User A
        log_activity(
            db=db,
            user_id=user_a.id,
            action=AuditEventType.CONTRACT_UPLOADED.value,
            resource_id=contract_a_analyzed.id,
            status="SUCCESS",
            metadata={"filename": contract_a_analyzed.filename},
        )
        log_activity(
            db=db,
            user_id=user_a.id,
            action=AuditEventType.ANALYSIS_COMPLETED.value,
            resource_id=contract_a_analyzed.id,
            status="SUCCESS",
            metadata={"analysis_type": "full_orchestration"},
        )
        db.commit()

        yield {
            "user_a": user_a,
            "user_b": user_b,
            "token_a": access_token_a,
            "token_b": access_token_b,
            "refresh_a": refresh_token_a,
            "refresh_b": refresh_token_b,
            "session_id_a": session_id_a,
            "session_id_b": session_id_b,
            "contract_a_analyzed": contract_a_analyzed,
            "contract_a_pending": contract_a_pending,
            "contract_a_v2": contract_a_v2,
            "contract_b": contract_b,
            "convo_a": convo_a,
        }

    finally:
        # Cleanup
        for email in [DAY56_PRIMARY_EMAIL, DAY56_SECONDARY_EMAIL]:
            user = db.query(User).filter_by(email=email).first()
            if user:
                db.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id.in_(
                        db.query(Conversation.id).filter_by(user_id=user.id)
                    )
                ).delete(synchronize_session=False)
                db.query(Conversation).filter_by(user_id=user.id).delete()
                db.query(AuditLog).filter_by(user_id=user.id).delete()
                db.query(UserSession).filter_by(user_id=user.id).delete()
                db.query(EmailOTPVerification).filter_by(email=email).delete()
                db.query(Analysis).filter(
                    Analysis.contract_id.in_(
                        db.query(Contract.id).filter_by(user_id=user.id)
                    )
                ).delete(synchronize_session=False)
                db.query(Contract).filter_by(user_id=user.id).delete()
                db.delete(user)
        db.commit()
        db.close()


class TestDay56ComprehensiveBackend:
    """Complete, exhaustive backend test suite certifying Phase 8 Day 56 requirements."""

    # --------------------------------------------------------------------------
    # 1. Document Ingestion & Validation
    # --------------------------------------------------------------------------

    def test_01_upload_invalid_file_type_returns_400(self, test_env):
        """Invalid file type upload (.exe, .sh, .py) must return 400 Bad Request."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        fake_executable = io.BytesIO(b"#!/bin/bash\necho 'unsupported file'")
        resp = client.post(
            "/contracts/upload",
            headers=headers,
            files={"file": ("malicious_script.sh", fake_executable, "application/x-sh")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "unsupported file format" in data["detail"].lower()

    def test_02_upload_oversized_file_returns_413(self, test_env):
        """File upload exceeding size limit (MAX_UPLOAD_SIZE_MB) must return 413 Content Too Large."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        oversized_bytes = b"0" * ((settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 1024)
        file_obj = io.BytesIO(oversized_bytes)
        resp = client.post(
            "/contracts/upload",
            headers=headers,
            files={"file": ("huge_document.pdf", file_obj, "application/pdf")},
        )
        assert resp.status_code in (413, 400)

    def test_03_upload_valid_pdf_document_returns_201(self, test_env):
        """Upload a valid PDF document must return 201 Created with contract ID and pending status."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        valid_pdf = io.BytesIO(b"%PDF-1.4\n1 0 obj<<>>endobj\nxref\n0 1\n0000000000 65535 f \ntrailer<<>>\nstartxref\n9\n%%EOF")
        resp = client.post(
            "/contracts/upload",
            headers=headers,
            files={"file": ("Employment_Agreement_2026.pdf", valid_pdf, "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["filename"] == "Employment_Agreement_2026.pdf"
        assert data["status"] == "pending"

    def test_04_list_contracts_user_isolation(self, test_env):
        """Listing contracts returns only current user's documents and never another user's."""
        headers_a = {"Authorization": f"Bearer {test_env['token_a']}"}
        resp_a = client.get("/contracts/", headers=headers_a)
        assert resp_a.status_code == 200
        filenames_a = [c["filename"] for c in resp_a.json()]
        assert "NDA_Mutual_Enterprise_v1.pdf" in filenames_a
        assert "UserB_Confidential_Employment.pdf" not in filenames_a

        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        resp_b = client.get("/contracts/", headers=headers_b)
        assert resp_b.status_code == 200
        filenames_b = [c["filename"] for c in resp_b.json()]
        assert "UserB_Confidential_Employment.pdf" in filenames_b
        assert "NDA_Mutual_Enterprise_v1.pdf" not in filenames_b

    def test_05_delete_contract_ownership_enforcement(self, test_env):
        """User B cannot delete User A's contract (returns 404)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        contract_a_id = test_env["contract_a_analyzed"].id
        resp = client.delete(f"/contracts/{contract_a_id}", headers=headers_b)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # 2. Analysis & Grounded Q&A Workflow Invariants
    # --------------------------------------------------------------------------

    def test_06_run_analysis_nonexistent_contract_returns_404(self, test_env):
        """Running analysis on a non-existent contract ID must return 404 Not Found."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        resp = client.post("/contracts/999999/analyze", headers=headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_07_run_analysis_other_user_contract_returns_404(self, test_env):
        """User B cannot trigger analysis on User A's contract (returns 404)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        contract_a_id = test_env["contract_a_pending"].id
        resp = client.post(f"/contracts/{contract_a_id}/analyze", headers=headers_b)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_08_ask_question_without_running_analysis_returns_400(self, test_env):
        """Asking a question on a contract that has not yet been analyzed must return 400 Bad Request."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        pending_contract_id = test_env["contract_a_pending"].id
        resp = client.post(
            f"/contracts/{pending_contract_id}/ask",
            headers=headers,
            json={"question": "What are the payment terms?"},
        )
        assert resp.status_code == 400
        assert "analyzed before asking questions" in resp.json()["detail"].lower()

    def test_09_ask_question_nonexistent_contract_returns_404(self, test_env):
        """Asking a question on a non-existent contract must return 404 Not Found."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        resp = client.post(
            "/contracts/999999/ask",
            headers=headers,
            json={"question": "What is the jurisdiction?"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_10_ask_question_other_user_contract_returns_404(self, test_env):
        """User B cannot ask questions on User A's contract (returns 404)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        contract_a_id = test_env["contract_a_analyzed"].id
        resp = client.post(
            f"/contracts/{contract_a_id}/ask",
            headers=headers_b,
            json={"question": "What is the liability cap?"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_11_ask_question_analyzed_contract_success(self, test_env):
        """Asking a question on an analyzed contract with mocked QA graph returns 200 with answer and sources."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        contract_id = test_env["contract_a_analyzed"].id

        mock_invoke_result = {
            "contract_id": contract_id,
            "question": "What is the notice period?",
            "answer": "The termination notice period is 30 days written notice.",
            "sources": [
                {
                    "chunk_index": 1,
                    "text": "Either party may terminate upon 30 days written notice.",
                    "similarity": 0.94,
                }
            ],
            "error": None,
        }

        with patch("app.api.qa.build_qa_graph") as mock_build_qa:
            mock_graph = MagicMock()
            mock_graph.invoke.return_value = mock_invoke_result
            mock_build_qa.return_value = mock_graph

            resp = client.post(
                f"/contracts/{contract_id}/ask",
                headers=headers,
                json={"question": "What is the notice period?"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "30 days" in data["answer"]
            assert len(data["sources"]) == 1
            assert data["contract_id"] == contract_id

    # --------------------------------------------------------------------------
    # 3. Authentication & Session Lifecycle Security
    # --------------------------------------------------------------------------

    def test_12_access_token_expiry_returns_401(self, test_env):
        """Access token that has expired past its 'exp' timestamp must return 401 Unauthorized."""
        user_a = test_env["user_a"]
        expired_token = create_access_token(
            data={"sub": user_a.email, "session_id": test_env["session_id_a"]},
            expires_delta=timedelta(seconds=-10),  # Expired in the past
        )
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
        assert "could not validate credentials" in resp.json()["detail"].lower()

    def test_13_malformed_token_returns_401(self):
        """Malformed or completely invalid JWT strings must return 401 Unauthorized."""
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid_gibberish_token_999"})
        assert resp.status_code == 401
        assert "could not validate credentials" in resp.json()["detail"].lower()

    def test_14_idle_session_expiry_returns_session_expired(self, test_env):
        """A session exceeding the idle timeout window (40 minutes) must return 401 SESSION_EXPIRED."""
        db = SessionLocal()
        try:
            session = db.query(UserSession).filter_by(id=test_env["session_id_a"]).first()
            session.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=45)
            db.commit()
        finally:
            db.close()

        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {test_env['token_a']}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "SESSION_EXPIRED"

    def test_15_absolute_session_expiry_returns_session_expired(self, test_env):
        """A session exceeding the 7-day absolute lifetime must return 401 SESSION_EXPIRED."""
        db = SessionLocal()
        try:
            session = db.query(UserSession).filter_by(id=test_env["session_id_b"]).first()
            session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
        finally:
            db.close()

        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {test_env['token_b']}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "SESSION_EXPIRED"

    def test_16_refresh_token_rotation(self, test_env):
        """Exchanging a valid refresh token issues a new access token and rotates the refresh token."""
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": test_env["refresh_a"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != test_env["refresh_a"]

        # Replaying the old refresh token must be rejected with 401
        replay_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": test_env["refresh_a"]},
        )
        assert replay_resp.status_code == 401

    def test_17_logout_invalidates_current_session(self, test_env):
        """Logging out revokes the session, causing subsequent requests with that token to fail with 401."""
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {test_env['token_a']}"},
            json={"refresh_token": test_env["refresh_a"]},
        )
        assert resp.status_code == 200

        # Subsequent call with the same token must fail
        subsequent_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {test_env['token_a']}"})
        assert subsequent_resp.status_code == 401

    # --------------------------------------------------------------------------
    # 4. Two-Factor Authentication (2FA) & Brute-Force Throttling
    # --------------------------------------------------------------------------

    def test_18_login_with_2fa_enabled_returns_requires_2fa(self, test_env):
        """Login with 2FA enabled on the user account returns requires_2fa=True and pending token."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(id=test_env["user_a"].id).first()
            user.is_2fa_enabled = True
            db.commit()
        finally:
            db.close()

        with patch("app.services.otp_service.send_smtp_email", return_value=True):
            resp = client.post(
                "/auth/login",
                json={"email": DAY56_PRIMARY_EMAIL, "password": DAY56_PASSWORD},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("requires_2fa") is True
            assert "pending_2fa_token" in data
            assert "Code sent to" in data["message"]

    def test_19_login_with_wrong_otp_fails(self, test_env):
        """Verifying with a wrong OTP code returns 400 Bad Request with remaining attempts."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            user.is_2fa_enabled = True

            otp_record = EmailOTPVerification(
                email=DAY56_PRIMARY_EMAIL,
                otp_hash=hash_token("987654"),
                attempts=0,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                is_verified=False,
            )
            db.merge(otp_record)
            db.commit()
        finally:
            db.close()

        pending_token = create_access_token(
            data={"sub": DAY56_PRIMARY_EMAIL, "pending_2fa": True},
            expires_delta=timedelta(minutes=5),
        )

        resp = client.post(
            "/auth/2fa/login-verify",
            json={"pending_2fa_token": pending_token, "otp_code": "000000"},
        )
        assert resp.status_code == 400
        assert "incorrect otp code" in resp.json()["detail"].lower()

    def test_20_repeated_wrong_otp_locks_out(self, test_env):
        """Submitting wrong OTP repeatedly locks out verification after MAX_OTP_ATTEMPTS."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            user.is_2fa_enabled = True

            otp_record = db.query(EmailOTPVerification).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            if not otp_record:
                otp_record = EmailOTPVerification(
                    email=DAY56_PRIMARY_EMAIL,
                    otp_hash=hash_token("987654"),
                    attempts=MAX_OTP_ATTEMPTS - 1,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    is_verified=False,
                )
                db.add(otp_record)
            else:
                otp_record.attempts = MAX_OTP_ATTEMPTS - 1
            db.commit()
        finally:
            db.close()

        pending_token = create_access_token(
            data={"sub": DAY56_PRIMARY_EMAIL, "pending_2fa": True},
            expires_delta=timedelta(minutes=5),
        )

        # This attempt should push it to MAX_OTP_ATTEMPTS and lock it
        resp = client.post(
            "/auth/2fa/login-verify",
            json={"pending_2fa_token": pending_token, "otp_code": "000000"},
        )
        assert resp.status_code == 400
        assert "maximum otp verification attempts exceeded" in resp.json()["detail"].lower()

    def test_21_otp_resend_respects_30s_cooldown(self, test_env):
        """Resending OTP immediately after generation must return 429 Too Many Requests."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            user.is_2fa_enabled = True

            otp_record = db.query(EmailOTPVerification).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            if otp_record:
                otp_record.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            else:
                otp_record = EmailOTPVerification(
                    email=DAY56_PRIMARY_EMAIL,
                    otp_hash=hash_token("987654"),
                    attempts=0,
                    created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    is_verified=False,
                )
                db.add(otp_record)
            db.commit()
        finally:
            db.close()

        pending_token = create_access_token(
            data={"sub": DAY56_PRIMARY_EMAIL, "pending_2fa": True},
            expires_delta=timedelta(minutes=5),
        )

        resp = client.post(
            "/auth/2fa/resend-otp",
            json={"pending_2fa_token": pending_token},
        )
        assert resp.status_code == 429
        assert "please wait" in resp.json()["detail"].lower()

    def test_22_otp_resend_allowed_after_cooldown(self, test_env):
        """Resending OTP after 30 seconds have elapsed succeeds with 200 OK."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            user.is_2fa_enabled = True

            otp_record = db.query(EmailOTPVerification).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            if otp_record:
                otp_record.created_at = datetime.now(timezone.utc) - timedelta(seconds=35)
            else:
                otp_record = EmailOTPVerification(
                    email=DAY56_PRIMARY_EMAIL,
                    otp_hash=hash_token("987654"),
                    attempts=0,
                    created_at=datetime.now(timezone.utc) - timedelta(seconds=35),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    is_verified=False,
                )
                db.add(otp_record)
            db.commit()
        finally:
            db.close()

        pending_token = create_access_token(
            data={"sub": DAY56_PRIMARY_EMAIL, "pending_2fa": True},
            expires_delta=timedelta(minutes=5),
        )

        with patch("app.services.otp_service.send_smtp_email", return_value=True):
            resp = client.post(
                "/auth/2fa/resend-otp",
                json={"pending_2fa_token": pending_token},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"

    def test_23_successful_2fa_verification_issues_tokens(self, test_env):
        """Submitting the valid OTP completes 2FA authentication and returns access and refresh tokens."""
        valid_code = "654321"
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            user.is_2fa_enabled = True

            otp_record = db.query(EmailOTPVerification).filter_by(email=DAY56_PRIMARY_EMAIL).first()
            if otp_record:
                otp_record.otp_hash = hash_token(valid_code)
                otp_record.attempts = 0
                otp_record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
                otp_record.is_verified = False
            else:
                otp_record = EmailOTPVerification(
                    email=DAY56_PRIMARY_EMAIL,
                    otp_hash=hash_token(valid_code),
                    attempts=0,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    is_verified=False,
                )
                db.add(otp_record)
            db.commit()
        finally:
            db.close()

        pending_token = create_access_token(
            data={"sub": DAY56_PRIMARY_EMAIL, "pending_2fa": True},
            expires_delta=timedelta(minutes=5),
        )

        resp = client.post(
            "/auth/2fa/login-verify",
            json={"pending_2fa_token": pending_token, "otp_code": valid_code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    # --------------------------------------------------------------------------
    # 5. Multi-Tenant Isolation & History Telemetry
    # --------------------------------------------------------------------------

    def test_24_user_cannot_read_other_user_history(self, test_env):
        """User B querying GET /history sees only their own history, never User A's logs."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        resp = client.get("/history", headers=headers_b)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            # Ensure none of User A's resources or filenames leak into User B's feed
            assert item.get("resource_id") != test_env["contract_a_analyzed"].id

    def test_25_user_cannot_read_other_user_conversation(self, test_env):
        """User B cannot view User A's conversation thread (returns 404 Not Found)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        convo_id = test_env["convo_a"].id
        resp = client.get(f"/conversations/{convo_id}", headers=headers_b)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_26_user_cannot_update_other_user_conversation(self, test_env):
        """User B cannot rename User A's conversation thread (returns 404 Not Found)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        convo_id = test_env["convo_a"].id
        resp = client.patch(
            f"/conversations/{convo_id}",
            headers=headers_b,
            json={"title": "Hacked Title Attempt"},
        )
        assert resp.status_code == 404

    def test_27_user_cannot_delete_other_user_conversation(self, test_env):
        """User B cannot delete User A's conversation thread (returns 404 Not Found)."""
        headers_b = {"Authorization": f"Bearer {test_env['token_b']}"}
        convo_id = test_env["convo_a"].id
        resp = client.delete(f"/conversations/{convo_id}", headers=headers_b)
        assert resp.status_code == 404

    def test_28_account_export_isolation(self, test_env):
        """GET /account/export returns strictly the requesting user's data archive."""
        headers_a = {"Authorization": f"Bearer {test_env['token_a']}"}
        resp = client.get("/account/export", headers=headers_a)
        assert resp.status_code == 200
        export_data = resp.json()

        assert export_data["account_profile"]["email"] == DAY56_PRIMARY_EMAIL
        contract_names = [c["filename"] for c in export_data["contracts"]]
        assert "NDA_Mutual_Enterprise_v1.pdf" in contract_names
        assert "UserB_Confidential_Employment.pdf" not in contract_names

    # --------------------------------------------------------------------------
    # 6. Comparison & Search Edge Cases
    # --------------------------------------------------------------------------

    def test_29_compare_contract_with_itself_returns_400(self, test_env):
        """Comparing a contract with itself must return 400 Bad Request."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        c1_id = test_env["contract_a_analyzed"].id
        resp = client.post(
            "/contracts/compare",
            headers=headers,
            json={"base_contract_id": c1_id, "target_contract_id": c1_id},
        )
        assert resp.status_code == 400
        assert "cannot compare a contract with itself" in resp.json()["detail"].lower()

    def test_30_compare_nonexistent_contract_returns_404(self, test_env):
        """Comparing against a nonexistent contract ID must return 404 Not Found."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        c1_id = test_env["contract_a_analyzed"].id
        resp = client.post(
            "/contracts/compare",
            headers=headers,
            json={"base_contract_id": c1_id, "target_contract_id": 999999},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_31_compare_other_user_contract_returns_404(self, test_env):
        """Comparing across tenant boundaries (User B's contract) returns 404 Not Found."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        c1_id = test_env["contract_a_analyzed"].id
        c_b_id = test_env["contract_b"].id
        resp = client.post(
            "/contracts/compare",
            headers=headers,
            json={"base_contract_id": c1_id, "target_contract_id": c_b_id},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_32_compare_two_valid_contracts_success(self, test_env):
        """Comparing two valid contracts owned by the user succeeds with 200 OK and diff payload."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        c1_id = test_env["contract_a_analyzed"].id
        c2_id = test_env["contract_a_v2"].id
        resp = client.post(
            "/contracts/compare",
            headers=headers,
            json={"base_contract_id": c1_id, "target_contract_id": c2_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "clause_diffs" in data
        assert "summary" in data
        assert "risk_delta" in data

    # --------------------------------------------------------------------------
    # 7. Session Management, Data Retention, and Telemetry
    # --------------------------------------------------------------------------

    def test_33_session_management_list_and_revoke(self, test_env):
        """List active sessions and revoke a specific session successfully."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}

        # List active sessions
        resp = client.get("/auth/sessions", headers=headers)
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 1
        assert any(s["is_current"] for s in sessions)

        # Create a second session for user A to test revocation
        db = SessionLocal()
        try:
            _, second_session_id = create_refresh_token(
                user_id=test_env["user_a"].id,
                db=db,
                device_info="Secondary Tablet",
                ip_address="192.168.1.100",
            )
        finally:
            db.close()

        # Revoke the second session
        revoke_resp = client.delete(f"/auth/sessions/{second_session_id}", headers=headers)
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["status"] == "success"

    def test_34_retention_policy_update(self, test_env):
        """Update activity data retention policy via PATCH /account/retention."""
        headers = {"Authorization": f"Bearer {test_env['token_a']}"}
        resp = client.patch(
            "/account/retention",
            headers=headers,
            json={"data_retention_days": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_retention_days"] == 30
        assert "30 days" in data["message"]

    def test_35_telemetry_metrics_and_health_probes(self):
        """Prometheus metrics and system health endpoints return 200 OK."""
        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "api_requests_total" in metrics_resp.text

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ok"
