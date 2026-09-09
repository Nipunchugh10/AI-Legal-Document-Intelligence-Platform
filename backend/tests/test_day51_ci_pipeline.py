"""
Day 51 Test Suite — Continuous Integration (CI) End-to-End Test Suite
======================================================================
Verifies all core critical platform journeys:
1. User Registration & Duplicate Email Protection
2. User Authentication & Login Verification
3. Token Refresh & Cryptographic Token Rotation
4. Session Invalidation on Logout & Idle Expiry
5. Email OTP 2FA Generation, Verification & Brute-Force Throttling
6. File Ingestion Validation (Unsupported Types & File Size Enforcement)
7. Contract Creation & Ownership Metadata
8. Analysis Workflow Execution (Mocked LLM / Cached Parsing)
9. Multi-Tenant Privacy & Data Isolation (Contracts, Conversations, Audit Logs, Export)
10. GitHub Actions CI Workflow Structure & Syntax Validation
"""

import io
import os
import sys
import yaml
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.core.security import (
    hash_password,
    verify_password,
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
from app.services.otp_service import send_otp, verify_otp, MAX_OTP_ATTEMPTS
from app.services.audit_logger import log_activity
from app.core.audit_events import AuditEventType

client = TestClient(app)

CI_USER_EMAIL = "ci_pipeline_lawyer@example.com"
CI_ATTACKER_EMAIL = "ci_intruder@example.com"
CI_PASSWORD = "SecurePassword2026!"


@pytest.fixture(scope="function")
def setup_ci_environment():
    """Sets up clean test users and contracts for CI pipeline test suite."""
    db = SessionLocal()
    try:
        # Purge test users if existing
        for email in [CI_USER_EMAIL, CI_ATTACKER_EMAIL]:
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

        # Create Primary CI User
        primary_user = User(
            email=CI_USER_EMAIL,
            hashed_password=hash_password(CI_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(primary_user)

        # Create Secondary / Attacker User for Multi-Tenancy Isolation
        attacker_user = User(
            email=CI_ATTACKER_EMAIL,
            hashed_password=hash_password(CI_PASSWORD),
            is_active=True,
            is_2fa_enabled=False,
            data_retention_days=None,
        )
        db.add(attacker_user)
        db.commit()
        db.refresh(primary_user)
        db.refresh(attacker_user)

        # Create contract for primary user
        primary_contract = Contract(
            filename="CI_Confidential_Master_Services_Agreement.pdf",
            upload_path="/tmp/ci_test_contract.pdf",
            status="analyzed",
            user_id=primary_user.id,
        )
        db.add(primary_contract)
        db.commit()
        db.refresh(primary_contract)

        # Create cached analysis for primary contract
        primary_analysis = Analysis(
            contract_id=primary_contract.id,
            analysis_type="parsing_agent",
            result_json={
                "document_type": "Master Services Agreement",
                "party_a": "Alpha Corp",
                "party_b": "Beta LLC",
                "effective_date": "2026-01-01",
                "jurisdiction": "Delaware",
                "summary": "Master Services Agreement between Alpha Corp and Beta LLC.",
            },
        )
        db.add(primary_analysis)
        db.commit()

        # Create conversation for primary user
        primary_convo = Conversation(
            user_id=primary_user.id,
            contract_id=primary_contract.id,
            title="CI Discussion on Termination Clauses",
        )
        db.add(primary_convo)
        db.commit()
        db.refresh(primary_convo)

        # Add message to conversation
        msg = ConversationMessage(
            conversation_id=primary_convo.id,
            role="user",
            content="What are the termination notice requirements?",
            cited_clause_refs=[{"chunk": 1, "text": "Notice of 30 days required"}],
        )
        db.add(msg)

        # Log activity
        log_activity(
            db=db,
            user_id=primary_user.id,
            action=AuditEventType.CONTRACT_UPLOADED,
            resource_id=primary_contract.id,
            metadata={"filename": primary_contract.filename},
        )
        db.commit()

        yield {
            "primary_user": primary_user,
            "attacker_user": attacker_user,
            "primary_contract": primary_contract,
            "primary_convo": primary_convo,
        }

    finally:
        # Cleanup
        for email in [CI_USER_EMAIL, CI_ATTACKER_EMAIL]:
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


class TestDay51CIPipeline:
    """20 Required Backend Tests for CI Pipeline Certification."""

    # --------------------------------------------------------------------------
    # 1. Authentication & Registration
    # --------------------------------------------------------------------------
    def test_01_user_registration_success(self):
        """Tests that a new user can register successfully with valid credentials."""
        email = f"new_ci_user_{int(datetime.now(timezone.utc).timestamp())}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": CI_PASSWORD},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["email"] == email
        assert "id" in data
        assert data.get("is_2fa_enabled") is False

    def test_02_user_registration_duplicate_email(self, setup_ci_environment):
        """Tests that duplicate user registration is prevented with 400 Bad Request."""
        resp = client.post(
            "/auth/register",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"].lower()
        assert "credentials" in detail or "already" in detail or "exists" in detail

    def test_03_user_login_success(self, setup_ci_environment):
        """Tests that user login returns access and refresh tokens and creates session."""
        resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data.get("requires_2fa") is False

    def test_04_user_login_invalid_credentials(self, setup_ci_environment):
        """Tests that user login with an invalid password returns 401 Unauthorized."""
        resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # 2. Session Management & Refresh
    # --------------------------------------------------------------------------
    def test_05_session_refresh_token_rotation(self, setup_ci_environment):
        """Tests that refreshing tokens rotates the refresh token and yields new credentials."""
        # Login first
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        old_refresh = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert refresh_resp.status_code == 200
        new_data = refresh_resp.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != old_refresh

    def test_06_session_refresh_with_invalid_token(self):
        """Tests that refresh with a forged or invalid token returns 401 Unauthorized."""
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": "completely_invalid_random_string_token"},
        )
        assert resp.status_code == 401

    def test_07_user_logout_revokes_session(self, setup_ci_environment):
        """Tests that logout revokes the user's active session in the database."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        logout_resp = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert logout_resp.status_code == 200
        assert "logged out" in logout_resp.json()["message"].lower()

        # Verify refresh token is now revoked
        post_refresh = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert post_refresh.status_code == 401

    def test_08_idle_session_expiry_enforcement(self, setup_ci_environment):
        """Tests that a session that has exceeded the idle timeout window is expired."""
        db = SessionLocal()
        try:
            user = setup_ci_environment["primary_user"]
            plain_token, session_id = create_refresh_token(user_id=user.id, db=db)
            session = db.query(UserSession).filter_by(id=session_id).first()
            # Set last_active_at to 60 minutes ago (> 40 min idle timeout)
            session.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=60)
            db.commit()

            access_token = create_access_token(data={"sub": user.email, "session_id": session.id})
            headers = {"Authorization": f"Bearer {access_token}"}

            # Attempt accessing protected endpoint
            resp = client.get("/auth/me", headers=headers)
            assert resp.status_code == 401
            assert "expired" in resp.json()["detail"].lower()
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 3. Two-Factor Authentication (Email OTP)
    # --------------------------------------------------------------------------
    def test_09_email_otp_generation_and_storage(self, setup_ci_environment):
        """Tests generating and storing an OTP in the database."""
        db = SessionLocal()
        try:
            send_otp(db, CI_USER_EMAIL)
            otp_record = db.query(EmailOTPVerification).filter_by(email=CI_USER_EMAIL).first()
            assert otp_record is not None
            assert otp_record.otp_hash is not None
            assert otp_record.attempts == 0
            assert otp_record.expires_at > datetime.now(timezone.utc)
        finally:
            db.close()

    def test_10_email_otp_login_verification_flow(self, setup_ci_environment):
        """Tests the full Email OTP 2FA login verification flow."""
        db = SessionLocal()
        try:
            # Enable 2FA on primary user
            user = setup_ci_environment["primary_user"]
            db_user = db.query(User).filter_by(id=user.id).first()
            db_user.is_2fa_enabled = True
            db.commit()

            # Attempt login -> should require 2FA
            login_resp = client.post(
                "/auth/login",
                json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
            )
            assert login_resp.status_code == 200
            data = login_resp.json()
            assert data.get("requires_2fa") is True
            pending_2fa_token = data.get("pending_2fa_token")
            assert pending_2fa_token is not None

            # Verify OTP
            with patch("app.services.otp_service.verify_otp", return_value=True):
                verify_resp = client.post(
                    "/auth/2fa/login-verify",
                    json={"pending_2fa_token": pending_2fa_token, "otp_code": "123456"},
                )
                assert verify_resp.status_code == 200
                v_data = verify_resp.json()
                assert "access_token" in v_data
                assert "refresh_token" in v_data
        finally:
            db.close()

    def test_11_email_otp_attempt_throttling(self, setup_ci_environment):
        """Tests that exceeding max OTP attempts locks the verification request."""
        db = SessionLocal()
        try:
            send_otp(db, CI_USER_EMAIL)
            
            # Submit wrong OTP codes up to the limit
            for _ in range(MAX_OTP_ATTEMPTS):
                try:
                    verify_otp(db, CI_USER_EMAIL, "000000")
                except Exception:
                    pass

            # Next attempt must fail with attempt exceeded
            with pytest.raises(Exception) as exc:
                verify_otp(db, CI_USER_EMAIL, "000000")
            assert "Maximum OTP verification attempts exceeded" in str(exc.value)
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 4. File Ingestion & Contract Creation
    # --------------------------------------------------------------------------
    def test_12_file_upload_validation_unsupported_type(self, setup_ci_environment):
        """Tests that uploading an unsupported file format (e.g. .exe) is rejected with 400."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create malicious fake executable file
        fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00BinaryData")
        files = {"file": ("malicious.exe", fake_exe, "application/octet-stream")}

        resp = client.post("/contracts/upload", files=files, headers=headers)
        assert resp.status_code == 400
        assert "unsupported file format" in resp.json()["detail"].lower()

    def test_13_file_upload_validation_size_limit(self, setup_ci_environment):
        """Tests that files exceeding the maximum size limit are rejected with 413 or 400."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create oversized file (11MB > 10MB limit)
        oversized = io.BytesIO(b"0" * (11 * 1024 * 1024))
        files = {"file": ("huge_contract.pdf", oversized, "application/pdf")}

        resp = client.post("/contracts/upload", files=files, headers=headers)
        assert resp.status_code in (400, 413)
        assert "exceeds" in resp.json()["detail"].lower()

    def test_14_contract_creation_and_metadata_persistence(self, setup_ci_environment):
        """Tests uploading a valid document persists contract metadata and pending status."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        contract_content = b"MUTUAL NON-DISCLOSURE AGREEMENT\nThis agreement is made between Party A and Party B."
        files = {"file": ("NDA_Sample_CI.txt", io.BytesIO(contract_content), "text/plain")}

        resp = client.post("/contracts/upload", files=files, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["filename"] == "NDA_Sample_CI.txt"
        assert data["status"] == "pending"
        assert "id" in data

    def test_15_contract_retrieval_and_ownership(self, setup_ci_environment):
        """Tests retrieving contract details as the authenticated owner."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        contract_id = setup_ci_environment["primary_contract"].id

        resp = client.get(f"/contracts/{contract_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == contract_id
        assert data["filename"] == "CI_Confidential_Master_Services_Agreement.pdf"

    # --------------------------------------------------------------------------
    # 5. Analysis Workflow Execution
    # --------------------------------------------------------------------------
    def test_16_analysis_workflow_triggering_with_mocked_llm(self, setup_ci_environment):
        """Tests triggering the AI analysis workflow and retrieving document parsing output."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_USER_EMAIL, "password": CI_PASSWORD},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        contract_id = setup_ci_environment["primary_contract"].id

        resp = client.post(f"/contracts/{contract_id}/analyze/parse", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_id"] == contract_id
        assert data["document_type"] == "Master Services Agreement"
        assert data["party_a"] == "Alpha Corp"
        assert data["party_b"] == "Beta LLC"

    # --------------------------------------------------------------------------
    # 6. Multi-Tenant Privacy & Data Isolation
    # --------------------------------------------------------------------------
    def test_17_multi_tenant_isolation_contracts(self, setup_ci_environment):
        """Verifies User A cannot read or mutate User B's contracts (returns 404)."""
        # Login as attacker
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_ATTACKER_EMAIL, "password": CI_PASSWORD},
        )
        attacker_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {attacker_token}"}
        primary_contract_id = setup_ci_environment["primary_contract"].id

        # Attacker tries to read Primary User's contract
        get_resp = client.get(f"/contracts/{primary_contract_id}", headers=headers)
        assert get_resp.status_code == 404

        # Attacker tries to delete Primary User's contract
        del_resp = client.delete(f"/contracts/{primary_contract_id}", headers=headers)
        assert del_resp.status_code == 404

    def test_18_multi_tenant_isolation_conversations(self, setup_ci_environment):
        """Verifies User A cannot view User B's Q&A conversations (returns 404)."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_ATTACKER_EMAIL, "password": CI_PASSWORD},
        )
        attacker_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {attacker_token}"}
        primary_convo_id = setup_ci_environment["primary_convo"].id

        # Attacker tries to read Primary User's conversation
        convo_resp = client.get(f"/conversations/{primary_convo_id}", headers=headers)
        assert convo_resp.status_code == 404

    def test_19_multi_tenant_isolation_history_and_export(self, setup_ci_environment):
        """Verifies User A's history and export contain zero records belonging to User B."""
        login_resp = client.post(
            "/auth/login",
            json={"email": CI_ATTACKER_EMAIL, "password": CI_PASSWORD},
        )
        attacker_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {attacker_token}"}

        # Check history feed
        hist_resp = client.get("/history", headers=headers)
        assert hist_resp.status_code == 200
        logs = hist_resp.json().get("logs", [])
        for entry in logs:
            assert entry.get("resource_id") != setup_ci_environment["primary_contract"].id

        # Check full data export
        export_resp = client.get("/account/export", headers=headers)
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["account_profile"]["email"] == CI_ATTACKER_EMAIL
        assert len(export_data["contracts"]) == 0
        assert len(export_data["conversations"]) == 0

    # --------------------------------------------------------------------------
    # 7. CI Workflow Structure & YAML Validation
    # --------------------------------------------------------------------------
    def test_20_ci_workflow_structure_validation(self):
        """Verifies that .github/workflows/ci.yml is valid YAML and defines all required CI jobs."""
        ci_file = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
        assert ci_file.exists(), ".github/workflows/ci.yml must exist"

        with open(ci_file, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        assert "name" in workflow
        assert ("on" in workflow or True in workflow)
        jobs = workflow.get("jobs", {})

        # Verify essential jobs exist
        assert "backend-tests" in jobs, "CI workflow must have 'backend-tests' job"
        assert "frontend-checks" in jobs, "CI workflow must have 'frontend-checks' job"
        assert "docker-validation" in jobs, "CI workflow must have 'docker-validation' job"

        # Verify backend-tests job services
        backend_job = jobs["backend-tests"]
        assert "services" in backend_job
        assert "postgres" in backend_job["services"]
        assert "postgres:15-alpine" in backend_job["services"]["postgres"]["image"]

        # Verify steps
        step_names = [step.get("name", "").lower() for step in backend_job.get("steps", [])]
        assert any("checkout" in name for name in step_names)
        assert any("python" in name for name in step_names)
        assert any("alembic" in name or "migration" in name for name in step_names)
        assert any("pytest" in name or "test" in name for name in step_names)
