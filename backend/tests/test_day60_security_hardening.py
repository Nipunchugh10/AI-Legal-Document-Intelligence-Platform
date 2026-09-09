"""
Day 60 — Security Hardening Test Suite
======================================
Comprehensive verification of platform-wide security controls:
1. HTTP Security Headers (nosniff, frame protection, CSP, referrer policy, permissions).
2. TrustedHostMiddleware (host header injection and poisoning prevention).
3. Multi-Tenant Data Boundary Validation (strict isolation across contracts, analyses, text, Q&A, conversations, comparisons, search, and history).
4. File Upload Path Traversal Defense & Filename Sanitization.
5. Cryptographic Hashing At Rest & Sensitive Credential Log Scrubbing.
"""

import io
import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import get_settings, Settings
from app.core.database import get_db, SessionLocal
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    create_access_token,
    create_refresh_token,
    sanitize_upload_filename,
)
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.email_otp import EmailOTPVerification
from app.models.user_session import UserSession
from app.models.audit_log import AuditLog
from app.services.audit_logger import sanitize_audit_metadata, log_activity
from app.services.otp_service import send_otp

client = TestClient(app)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_session():
    """Provides a transactional database session for setup and teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def tenant_users(db_session: Session):
    """Creates two distinct users for strict multi-tenant boundary verification."""
    # User A (Alice)
    user_a = db_session.query(User).filter(User.email == "sec_alice@example.com").first()
    if not user_a:
        user_a = User(
            email="sec_alice@example.com",
            hashed_password=hash_password("AliceSecurePass123!"),
            is_active=True,
            is_2fa_enabled=False,
        )
        db_session.add(user_a)

    # User B (Bob)
    user_b = db_session.query(User).filter(User.email == "sec_bob@example.com").first()
    if not user_b:
        user_b = User(
            email="sec_bob@example.com",
            hashed_password=hash_password("BobSecurePass456!"),
            is_active=True,
            is_2fa_enabled=False,
        )
        db_session.add(user_b)

    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    # Generate valid sessions & tokens for both users
    raw_token_a, sess_a_id = create_refresh_token(user_a.id, db_session)
    token_a = create_access_token({"sub": user_a.email, "session_id": sess_a_id})

    raw_token_b, sess_b_id = create_refresh_token(user_b.id, db_session)
    token_b = create_access_token({"sub": user_b.email, "session_id": sess_b_id})

    return {
        "user_a": user_a,
        "token_a": token_a,
        "session_a_id": sess_a_id,
        "user_b": user_b,
        "token_b": token_b,
        "session_b_id": sess_b_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. HTTP Security Headers Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestSecurityHeaders:
    """Verifies that HTTP responses contain enterprise-grade security headers."""

    def test_01_universal_security_headers_present(self):
        """Validates that nosniff, strict referrer, and permissions policies are injected."""
        response = client.get("/health")
        assert response.status_code == 200
        headers = response.headers

        # MIME sniffing protection
        assert headers.get("X-Content-Type-Options") == "nosniff"
        # Referrer privacy
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        # Hardware permissions restriction
        assert headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"
        # Legacy XSS filter enable
        assert headers.get("X-XSS-Protection") == "1; mode=block"

    def test_02_frame_ancestors_or_x_frame_options(self):
        """Verifies clickjacking protection via X-Frame-Options or CSP frame-ancestors."""
        response = client.get("/health")
        headers = response.headers

        has_x_frame = "X-Frame-Options" in headers
        has_csp = "Content-Security-Policy" in headers

        assert has_x_frame or has_csp
        if has_csp:
            assert "frame-ancestors" in headers["Content-Security-Policy"]
        elif has_x_frame:
            assert headers["X-Frame-Options"] in {"DENY", "SAMEORIGIN"}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Host Header Validation & TrustedHostMiddleware
# ─────────────────────────────────────────────────────────────────────────────

class TestTrustedHostMiddleware:
    """Tests rejection of forged or malicious Host headers."""

    def test_03_trusted_hosts_accepted(self):
        """Requests with legitimate host headers (testserver, localhost, hf.space) succeed."""
        for host in ["testserver", "localhost", "127.0.0.1"]:
            resp = client.get("/health", headers={"Host": host})
            assert resp.status_code == 200

    def test_04_untrusted_host_rejected(self):
        """Requests with an untrusted or spoofed Host header must return 400 Bad Request."""
        resp = client.get("/health", headers={"Host": "evil-attacker.com"})
        assert resp.status_code == 400
        assert "Invalid host header" in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 3. Multi-Tenant Data Boundary & Tenancy Isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiTenantDataBoundary:
    """Verifies that User B cannot access, mutate, or inspect User A's resources."""

    @pytest.fixture(autouse=True)
    def setup_user_a_contract(self, db_session: Session, tenant_users: dict):
        self.user_a = tenant_users["user_a"]
        self.token_a = tenant_users["token_a"]
        self.user_b = tenant_users["user_b"]
        self.token_b = tenant_users["token_b"]

        # Ensure User A has an analyzed contract in DB
        contract_a = (
            db_session.query(Contract)
            .filter(Contract.user_id == self.user_a.id, Contract.filename == "sec_contract_a.pdf")
            .first()
        )
        if not contract_a:
            contract_a = Contract(
                user_id=self.user_a.id,
                filename="sec_contract_a.pdf",
                upload_path="./test_uploads/sec_contract_a.pdf",
                status="analyzed",
            )
            db_session.add(contract_a)
            db_session.commit()
            db_session.refresh(contract_a)

        # Ensure analysis record exists
        analysis_a = (
            db_session.query(Analysis)
            .filter(Analysis.contract_id == contract_a.id, Analysis.analysis_type == "parsing_agent")
            .first()
        )
        if not analysis_a:
            analysis_a = Analysis(
                contract_id=contract_a.id,
                analysis_type="parsing_agent",
                result_json={"document_type": "Confidential NDA", "party_a": "Alice Corp"},
            )
            db_session.add(analysis_a)
            db_session.commit()

        # Ensure conversation thread exists for User A
        convo_a = (
            db_session.query(Conversation)
            .filter(Conversation.user_id == self.user_a.id, Conversation.contract_id == contract_a.id)
            .first()
        )
        if not convo_a:
            convo_a = Conversation(
                user_id=self.user_a.id,
                contract_id=contract_a.id,
                title="Alice Private Discussion",
            )
            db_session.add(convo_a)
            db_session.commit()
            db_session.refresh(convo_a)

            msg = ConversationMessage(
                conversation_id=convo_a.id,
                role="user",
                content="What is the confidential term?",
            )
            db_session.add(msg)
            db_session.commit()

        self.contract_a = contract_a
        self.convo_a = convo_a

    def test_05_user_b_cannot_get_user_a_contract(self):
        """User B cannot fetch User A's contract details."""
        resp = client.get(
            f"/contracts/{self.contract_a.id}",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_06_user_b_cannot_extract_user_a_contract(self):
        """User B cannot trigger text extraction on User A's contract."""
        resp = client.post(
            f"/contracts/{self.contract_a.id}/extract",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_07_user_b_cannot_analyze_user_a_contract(self):
        """User B cannot trigger analysis on User A's contract."""
        resp = client.post(
            f"/contracts/{self.contract_a.id}/analyze",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_08_user_b_cannot_get_user_a_analysis(self):
        """User B cannot fetch analysis findings for User A's contract."""
        resp = client.get(
            f"/contracts/{self.contract_a.id}/analysis",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_09_user_b_cannot_get_user_a_raw_text(self):
        """User B cannot fetch raw text for User A's contract."""
        resp = client.get(
            f"/contracts/{self.contract_a.id}/text",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_10_user_b_cannot_ask_qa_on_user_a_contract(self):
        """User B cannot query Q&A agent over User A's contract."""
        resp = client.post(
            f"/contracts/{self.contract_a.id}/ask",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"question": "What is the penalty?"},
        )
        assert resp.status_code == 404

    def test_11_user_b_cannot_delete_user_a_contract(self):
        """User B cannot delete User A's contract."""
        resp = client.delete(
            f"/contracts/{self.contract_a.id}",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_12_user_b_cannot_read_or_mutate_user_a_conversation(self):
        """User B cannot read, rename, or delete User A's conversation thread."""
        headers = {"Authorization": f"Bearer {self.token_b}"}

        # 1. Read attempt
        r_get = client.get(f"/conversations/{self.convo_a.id}", headers=headers)
        assert r_get.status_code == 404

        # 2. Rename attempt
        r_patch = client.patch(
            f"/conversations/{self.convo_a.id}",
            headers=headers,
            json={"title": "Hacked Title"},
        )
        assert r_patch.status_code == 404

        # 3. Delete attempt
        r_del = client.delete(f"/conversations/{self.convo_a.id}", headers=headers)
        assert r_del.status_code == 404

    def test_13_user_b_cannot_compare_user_a_contracts(self):
        """User B cannot supply User A's contract ID as base or target comparison operand."""
        headers = {"Authorization": f"Bearer {self.token_b}"}

        # Base contract is User A's
        resp = client.post(
            "/contracts/compare",
            headers=headers,
            json={"base_contract_id": self.contract_a.id, "target_contract_id": 99999},
        )
        assert resp.status_code == 404

    def test_14_user_b_history_does_not_contain_user_a_events(self):
        """User B's activity history does not contain User A's activities."""
        resp = client.get(
            "/history",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        for item in items:
            assert item.get("user_id") != self.user_a.id


# ─────────────────────────────────────────────────────────────────────────────
# 4. File Upload Path Traversal Defense & Sanitization
# ─────────────────────────────────────────────────────────────────────────────

class TestFileUploadPathTraversal:
    """Verifies protection against directory traversal and null-byte injection in uploads."""

    def test_15_sanitize_upload_filename_unit_logic(self):
        """Tests unit logic of sanitize_upload_filename across edge cases."""
        # 1. Basic safe filename
        assert sanitize_upload_filename("standard_contract.pdf") == "standard_contract.pdf"

        # 2. Path traversal with forward slashes
        assert sanitize_upload_filename("../../../etc/passwd.pdf") == "passwd.pdf"

        # 3. Path traversal with Windows backslashes
        assert sanitize_upload_filename("..\\..\\windows\\system32\\cmd.pdf") == "cmd.pdf"

        # 4. Leading dots and whitespace (hidden files)
        assert sanitize_upload_filename("   .hidden_payload.pdf   ") == "hidden_payload.pdf"

        # 5. Dangerous characters sanitized to underscores
        res = sanitize_upload_filename("contract;rm -rf;$(whoami).pdf")
        assert ";" not in res
        assert "$" not in res
        assert "(" not in res
        assert ")" not in res
        assert res.endswith(".pdf")

        # 6. Null bytes must raise 400
        with pytest.raises(HTTPException) as exc:
            sanitize_upload_filename("malicious\0contract.pdf")
        assert exc.value.status_code == 400

        # 7. Empty filename must raise 400
        with pytest.raises(HTTPException) as exc:
            sanitize_upload_filename("   ")
        assert exc.value.status_code == 400

    def test_16_upload_api_path_traversal_sanitized_and_contained(self, tenant_users: dict):
        """Upload API cleanly neutralizes directory traversal in filename."""
        token_a = tenant_users["token_a"]
        fake_pdf = b"%PDF-1.4 Mock Safe Legal Content For Day 60 Test"

        # Send file with traversal sequence
        response = client.post(
            "/contracts/upload",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("../../traversal_attack.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        )
        assert response.status_code == 201
        data = response.json()

        # Filename should have traversal stripped
        assert ".." not in data["filename"]
        assert "/" not in data["filename"]
        assert "\\" not in data["filename"]
        assert data["filename"] == "traversal_attack.pdf"

        # Physical file must exist inside the configured UPLOAD_DIR
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)
        upload_path = os.path.abspath(data["upload_path"])
        assert upload_path.startswith(upload_dir)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cryptographic Hashing At Rest & Sensitive Credential Log Scrubbing
# ─────────────────────────────────────────────────────────────────────────────

class TestCredentialsAtRestAndLogScrubbing:
    """Verifies that credentials are never stored in plain text or leaked in audit logs."""

    def test_17_user_passwords_are_bcrypt_hashed(self, db_session: Session, tenant_users: dict):
        """Users in database store bcrypt hashes starting with $2b$, never plain text."""
        user = db_session.query(User).filter(User.id == tenant_users["user_a"].id).first()
        assert user is not None
        assert user.hashed_password.startswith("$2b$")
        assert verify_password("AliceSecurePass123!", user.hashed_password) is True
        assert verify_password("WrongPassword", user.hashed_password) is False

    def test_18_email_otps_are_sha256_hashed(self, db_session: Session):
        """Email OTPs are stored as 64-character SHA-256 hashes, not raw 6-digit codes."""
        test_email = "otp_security_test@example.com"
        send_otp(db_session, test_email)

        otp_record = (
            db_session.query(EmailOTPVerification)
            .filter(EmailOTPVerification.email == test_email)
            .first()
        )
        assert otp_record is not None
        # SHA-256 is exactly 64 hex characters
        assert len(otp_record.otp_hash) == 64
        # Cannot be a plain 6-digit numeric string
        assert not (len(otp_record.otp_hash) == 6 and otp_record.otp_hash.isdigit())

    def test_19_refresh_tokens_are_sha256_hashed(self, db_session: Session, tenant_users: dict):
        """Refresh tokens in user_sessions are stored as 64-character hashes."""
        session = (
            db_session.query(UserSession)
            .filter(UserSession.id == tenant_users["session_a_id"])
            .first()
        )
        assert session is not None
        assert len(session.refresh_token_hash) == 64

    def test_20_audit_logger_metadata_scrubbing(self, db_session: Session, tenant_users: dict):
        """Audit logger automatically redacts sensitive keywords from metadata_json."""
        dirty_metadata = {
            "action_type": "user_auth",
            "password": "SuperSecretPassword123!",
            "submitted_otp": "654321",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
            "safe_param": "regular_value",
            "nested": {
                "api_key": "AIzaSySecretKey",
                "normal_field": 42,
            },
        }

        entry = log_activity(
            db=db_session,
            action="SECURITY_TEST_ACTION",
            user_id=tenant_users["user_a"].id,
            status="SUCCESS",
            metadata=dirty_metadata,
        )

        assert entry is not None
        meta = entry.metadata_json
        assert meta["password"] == "***REDACTED***"
        assert meta["submitted_otp"] == "***REDACTED***"
        assert meta["access_token"] == "***REDACTED***"
        assert meta["safe_param"] == "regular_value"
        assert meta["nested"]["api_key"] == "***REDACTED***"
        assert meta["nested"]["normal_field"] == 42

    def test_21_settings_repr_masks_secrets(self):
        """Settings.__repr__ redacts all sensitive secrets and passwords."""
        settings_repr = repr(settings)
        assert "JWT_SECRET_KEY='***REDACTED***'" in settings_repr
        assert "POSTGRES_PASSWORD='***REDACTED***'" in settings_repr
        assert "GEMINI_API_KEY='***REDACTED***'" in settings_repr
        assert "***REDACTED***" in settings_repr
