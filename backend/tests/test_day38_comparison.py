"""
Day 38 — Contract Comparison Tests
----------------------------------
Unit and integration tests for multi-version contract difference detection,
semantic clause diffing, and risk profile evolution.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.comparison_service import ComparisonService
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token

client = TestClient(app)
TEST_EMAIL = "compare_test_user@example.com"


def test_comparison_service_diff_segments():
    """Verifies that ComparisonService properly identifies equal, insert, delete, and replace segments."""
    base_text = "The vendor shall deliver the software within 30 days."
    target_text = "The vendor shall deliver the enhanced software within 45 business days."

    segments = ComparisonService.compute_diff_segments(base_text, target_text)
    assert len(segments) > 0
    assert any(s.operation == "insert" and "enhanced" in s.text for s in segments)
    assert any(s.operation == "delete" and "30" in s.text for s in segments)
    assert any(s.operation == "insert" and "45" in s.text for s in segments)


def test_comparison_service_clause_diff_classification():
    """Verifies that ComparisonService correctly categorizes ADDED, REMOVED, MODIFIED, and UNCHANGED clauses."""
    base_clauses = {
        "payment_terms": "Invoices are payable within 30 days of receipt.",
        "liability_clauses": "Liability is completely uncapped and unlimited.",
        "confidentiality_clauses": "Confidential information shall be kept private for 3 years.",
    }

    target_clauses = {
        "payment_terms": "Invoices are payable within 30 days of receipt.",  # UNCHANGED
        "liability_clauses": "Total liability is capped at fees paid in the last 12 months.",  # MODIFIED
        # confidentiality_clauses is missing -> REMOVED
        "dispute_resolution_clauses": "Disputes shall be resolved via arbitration in New Delhi.",  # ADDED
    }

    clause_diffs, added, removed, modified, unchanged = ComparisonService.compare_clauses(
        base_clauses, target_clauses
    )

    assert added == 1
    assert removed == 1
    assert modified == 1
    assert unchanged == 1

    diff_map = {d.clause_key: d for d in clause_diffs}
    assert diff_map["payment_terms"].status == "UNCHANGED"
    assert diff_map["liability_clauses"].status == "MODIFIED"
    assert diff_map["confidentiality_clauses"].status == "REMOVED"
    assert diff_map["dispute_resolution_clauses"].status == "ADDED"


def test_comparison_service_risk_delta():
    """Verifies that ComparisonService accurately computes risk score shift and flag count deltas."""
    base_risks = [
        {"flag_category": "RED_FLAG", "risk_type": "UNLIMITED_LIABILITY"},
        {"flag_category": "RED_FLAG", "risk_type": "ONE_SIDED_TERMINATION"},
        {"flag_category": "YELLOW_FLAG", "risk_type": "AMBIGUOUS_NOTICE"},
    ]

    target_risks = [
        {"flag_category": "YELLOW_FLAG", "risk_type": "AMBIGUOUS_NOTICE"},
        {"flag_category": "GREEN_FLAG", "risk_type": "MUTUAL_CONFIDENTIALITY"},
    ]

    delta = ComparisonService.compare_risk_profiles(base_risks, target_risks)

    assert delta.base_red_flags == 2
    assert delta.target_red_flags == 0
    assert delta.base_risk_score > delta.target_risk_score
    assert delta.score_delta < 0
    assert "Risk Reduced" in delta.assessment


@pytest.fixture
def auth_user_and_token():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if not user:
            user = User(
                email=TEST_EMAIL,
                hashed_password="hashed_test_password_123",
                is_active=True,
                is_2fa_enabled=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash="compare-test-session-hash-123",
            device_info="Test Client",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        token = create_access_token(
            data={"sub": user.email, "user_id": user.id, "session_id": session.id}
        )
        yield user, token

        # Cleanup
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()
        db.query(Analysis).filter(
            Analysis.contract_id.in_(
                db.query(Contract.id).filter(Contract.user_id == user.id)
            )
        ).delete(synchronize_session=False)
        db.query(Contract).filter(Contract.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    finally:
        db.close()


def test_compare_endpoint_unauthorized():
    """Verifies that POST /contracts/compare requires authentication."""
    response = client.post("/contracts/compare", json={"base_contract_id": 1, "target_contract_id": 2})
    assert response.status_code in [401, 403]


def test_compare_endpoint_not_found(auth_user_and_token):
    """Verifies that POST /contracts/compare returns 404 if contract is non-existent."""
    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/contracts/compare",
        json={"base_contract_id": 999999, "target_contract_id": 999998},
        headers=headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_compare_endpoint_success(auth_user_and_token):
    """Verifies that POST /contracts/compare successfully compares two user contracts with analysis records."""
    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        # Create base contract & analysis
        base_c = Contract(
            user_id=user.id,
            filename="master_agreement_v1.pdf",
            upload_path="/dummy/path/v1.pdf",
            status="analyzed",
        )
        target_c = Contract(
            user_id=user.id,
            filename="master_agreement_v2_revised.pdf",
            upload_path="/dummy/path/v2.pdf",
            status="analyzed",
        )
        db.add(base_c)
        db.add(target_c)
        db.commit()
        db.refresh(base_c)
        db.refresh(target_c)

        base_analysis = Analysis(
            contract_id=base_c.id,
            analysis_type="full_orchestration",
            result_json={
                "clauses": {
                    "payment_terms": "Payment due in 15 days.",
                    "liability_clauses": "Liability is uncapped.",
                },
                "risks": [{"flag_category": "RED_FLAG", "risk_type": "UNCAPPED_LIABILITY"}],
            },
        )
        target_analysis = Analysis(
            contract_id=target_c.id,
            analysis_type="full_orchestration",
            result_json={
                "clauses": {
                    "payment_terms": "Payment due in 30 days.",
                    "liability_clauses": "Liability is capped at $10,000.",
                },
                "risks": [{"flag_category": "GREEN_FLAG", "risk_type": "CAPPED_LIABILITY"}],
            },
        )
        db.add(base_analysis)
        db.add(target_analysis)
        db.commit()

        # Call comparison endpoint
        response = client.post(
            "/contracts/compare",
            json={"base_contract_id": base_c.id, "target_contract_id": target_c.id},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["base_contract_id"] == base_c.id
        assert data["target_contract_id"] == target_c.id
        assert data["base_filename"] == "master_agreement_v1.pdf"
        assert data["target_filename"] == "master_agreement_v2_revised.pdf"
        assert "metrics" in data
        assert data["metrics"]["clauses_modified_count"] >= 1
        assert "clause_diffs" in data
        assert len(data["clause_diffs"]) >= 2
        assert "risk_delta" in data
        assert data["risk_delta"]["base_red_flags"] == 1
        assert data["risk_delta"]["target_red_flags"] == 0
    finally:
        db.close()
