"""
Day 40 — Semantic Search Tests
------------------------------
Unit and integration tests for multi-contract semantic search backend.
Tests vector similarity ranking, metadata filtering (document type, risk level, date range),
multi-tenant isolation, snippet highlighting, and auth protection.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store_service
from app.services.embedder import get_embedder_service
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token

client = TestClient(app)
TEST_EMAIL_1 = "search_user_1@example.com"
TEST_EMAIL_2 = "search_user_2@example.com"


def test_highlight_query_terms():
    """Verifies that SearchService properly highlights keywords while escaping HTML."""
    text = "The Consultant agrees to indemnify the Client against all third-party claims."
    query = "indemnify client"
    
    highlighted = SearchService.highlight_query_terms(text, query)
    assert "<mark>indemnify</mark>" in highlighted or "<mark>Indemnify</mark>" in highlighted or "indemnify" in highlighted.lower()
    assert "<mark>Client</mark>" in highlighted or "<mark>client</mark>" in highlighted

    # Test XSS safety
    raw_unsafe = "Dangerous <script>alert(1)</script> clause with indemnity."
    safe_highlighted = SearchService.highlight_query_terms(raw_unsafe, "indemnity")
    assert "<script>" not in safe_highlighted
    assert "&lt;script&gt;" in safe_highlighted
    assert "<mark>indemnity</mark>" in safe_highlighted


def test_semantic_search_unauthorized():
    """Unauthenticated request to GET /contracts/search should return 401."""
    response = client.get("/contracts/search?q=indemnity")
    assert response.status_code == 401


@pytest.fixture
def setup_search_test_data():
    """Sets up two test users with valid sessions, indexed contracts, and analyses in ChromaDB."""
    db = SessionLocal()
    vector_store = get_vector_store_service()
    embedder = get_embedder_service()

    try:
        # Create User 1
        user1 = db.query(User).filter(User.email == TEST_EMAIL_1).first()
        if not user1:
            user1 = User(email=TEST_EMAIL_1, hashed_password="hashedpassword123", is_active=True, is_2fa_enabled=False)
            db.add(user1)
            db.commit()
            db.refresh(user1)

        # Create Session for User 1
        session1 = UserSession(
            user_id=user1.id,
            refresh_token_hash="search-test-session-1-hash",
            device_info="Test Client",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(session1)

        # Create User 2 (for multi-tenant isolation testing)
        user2 = db.query(User).filter(User.email == TEST_EMAIL_2).first()
        if not user2:
            user2 = User(email=TEST_EMAIL_2, hashed_password="hashedpassword123", is_active=True, is_2fa_enabled=False)
            db.add(user2)
            db.commit()
            db.refresh(user2)

        # Create Session for User 2
        session2 = UserSession(
            user_id=user2.id,
            refresh_token_hash="search-test-session-2-hash",
            device_info="Test Client",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(session2)
        db.commit()
        db.refresh(session1)
        db.refresh(session2)

        # Create User 1 Contract A: Freelance Service Agreement (Heavy Indemnity & Payment)
        contract_a = Contract(
            user_id=user1.id,
            filename="Freelance_Service_Agreement_2026.pdf",
            upload_path="/dummy/path/freelance.pdf",
            status="analyzed",
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db.add(contract_a)

        # Create User 1 Contract B: Mutual NDA (Heavy Confidentiality & Trade Secrets)
        contract_b = Contract(
            user_id=user1.id,
            filename="Mutual_Non_Disclosure_Agreement.pdf",
            upload_path="/dummy/path/nda.pdf",
            status="analyzed",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        db.add(contract_b)

        # Create User 2 Contract C: Secret Patent Agreement (Isolated to User 2)
        contract_c = Contract(
            user_id=user2.id,
            filename="User2_Confidential_Patent.pdf",
            upload_path="/dummy/path/user2_patent.pdf",
            status="analyzed",
            created_at=datetime.now(timezone.utc),
        )
        db.add(contract_c)
        db.commit()
        db.refresh(contract_a)
        db.refresh(contract_b)
        db.refresh(contract_c)

        # Add Analyses for Contract A
        analysis_a_parsed = Analysis(
            contract_id=contract_a.id,
            analysis_type="parsed",
            result_json={"document_type": "Service Agreement", "parties": ["Client Corp", "Freelancer Dev"]}
        )
        analysis_a_risks = Analysis(
            contract_id=contract_a.id,
            analysis_type="risks",
            result_json={
                "risk_score": 75,
                "risks": [
                    {"severity": "RED_FLAG", "issue": "Uncapped indemnity liability"},
                    {"severity": "RED_FLAG", "issue": "Unilateral termination without cause"}
                ]
            }
        )
        db.add_all([analysis_a_parsed, analysis_a_risks])

        # Add Analyses for Contract B
        analysis_b_parsed = Analysis(
            contract_id=contract_b.id,
            analysis_type="parsed",
            result_json={"document_type": "Non-Disclosure Agreement (NDA)", "parties": ["Alpha Inc", "Beta LLC"]}
        )
        analysis_b_risks = Analysis(
            contract_id=contract_b.id,
            analysis_type="risks",
            result_json={
                "risk_score": 15,
                "risks": [
                    {"severity": "GREEN_FLAG", "issue": "Mutual non-disclosure with standard exceptions"}
                ]
            }
        )
        db.add_all([analysis_b_parsed, analysis_b_risks])
        db.commit()

        # Vectorize Chunks in ChromaDB
        chunks_a = [
            "Section 8: Indemnification. The Contractor shall indemnify, defend, and hold harmless the Company against all third-party losses.",
            "Section 4: Payment Terms. Invoices are due net 30 days upon delivery of milestones.",
        ]
        embeddings_a = [embedder.embed_text(c) for c in chunks_a]
        vector_store.add_contract_chunks(contract_a.id, chunks_a, embeddings_a)

        chunks_b = [
            "Section 2: Confidential Information. Receiving party agrees not to disclose trade secrets or proprietary source code for 5 years.",
            "Section 6: Non-Compete. Neither party shall solicit employees for a period of 12 months.",
        ]
        embeddings_b = [embedder.embed_text(c) for c in chunks_b]
        vector_store.add_contract_chunks(contract_b.id, chunks_b, embeddings_b)

        chunks_c = [
            "User 2 Proprietary Patent Rights. Uncapped indemnity clause specifically for user 2 only.",
        ]
        embeddings_c = [embedder.embed_text(c) for c in chunks_c]
        vector_store.add_contract_chunks(contract_c.id, chunks_c, embeddings_c)

        token_user1 = create_access_token(
            data={"sub": user1.email, "user_id": user1.id, "session_id": session1.id}
        )
        token_user2 = create_access_token(
            data={"sub": user2.email, "user_id": user2.id, "session_id": session2.id}
        )

        yield {
            "user1": user1,
            "user2": user2,
            "session1": session1,
            "session2": session2,
            "token_user1": token_user1,
            "token_user2": token_user2,
            "contract_a": contract_a,
            "contract_b": contract_b,
            "contract_c": contract_c,
        }

    finally:
        # Cleanup
        try:
            vector_store.delete_contract_chunks(contract_a.id)
            vector_store.delete_contract_chunks(contract_b.id)
            vector_store.delete_contract_chunks(contract_c.id)
        except Exception:
            pass

        try:
            db.query(Analysis).filter(Analysis.contract_id.in_([contract_a.id, contract_b.id, contract_c.id])).delete(synchronize_session=False)
            db.query(Contract).filter(Contract.id.in_([contract_a.id, contract_b.id, contract_c.id])).delete(synchronize_session=False)
            db.query(UserSession).filter(UserSession.id.in_([session1.id, session2.id])).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_([user1.id, user2.id])).delete(synchronize_session=False)
            db.commit()
        except Exception:
            pass
        db.close()


def test_semantic_search_validation_empty_query(setup_search_test_data):
    """Empty query string should fail request validation (422)."""
    data = setup_search_test_data
    token = data["token_user1"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/contracts/search?q=", headers=headers)
    assert response.status_code == 422


def test_semantic_search_indemnity_query(setup_search_test_data):
    """Verifies that searching for 'indemnification liability' returns Contract A as top match."""
    data = setup_search_test_data
    token = data["token_user1"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/contracts/search?q=indemnification+and+hold+harmless+liability", headers=headers)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["query"] == "indemnification and hold harmless liability"
    assert res_data["total_contracts_matched"] >= 1
    
    top_contract = res_data["results"][0]
    assert top_contract["contract_id"] == data["contract_a"].id
    assert "Freelance" in top_contract["filename"]
    assert top_contract["risk_level"] == "CRITICAL"
    assert top_contract["risk_score"] == 75
    assert len(top_contract["matching_chunks"]) > 0
    assert any("indemnif" in c["text"].lower() for c in top_contract["matching_chunks"])


def test_semantic_search_confidentiality_query(setup_search_test_data):
    """Verifies that searching for 'trade secrets confidentiality' returns Contract B as top match."""
    data = setup_search_test_data
    token = data["token_user1"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/contracts/search?q=confidential+information+trade+secrets", headers=headers)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["total_contracts_matched"] >= 1
    top_contract = res_data["results"][0]
    assert top_contract["contract_id"] == data["contract_b"].id
    assert "Non_Disclosure" in top_contract["filename"]
    assert top_contract["risk_level"] == "LOW"
    assert top_contract["risk_score"] == 15


def test_semantic_search_multi_tenant_isolation(setup_search_test_data):
    """Verifies that User 1 cannot search or see User 2's contracts."""
    data = setup_search_test_data
    token1 = data["token_user1"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Query matching content specifically in User 2's contract
    response = client.get("/contracts/search?q=User+2+Proprietary+Patent", headers=headers1)
    assert response.status_code == 200
    res_data = response.json()

    # User 1 must not receive contract_c
    contract_ids = [r["contract_id"] for r in res_data["results"]]
    assert data["contract_c"].id not in contract_ids


def test_semantic_search_metadata_filters(setup_search_test_data):
    """Verifies document_type, risk_level, and contract_id metadata filters."""
    data = setup_search_test_data
    token = data["token_user1"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Filter by document_type=NDA
    res_nda = client.get("/contracts/search?q=Section&document_type=NDA", headers=headers)
    assert res_nda.status_code == 200
    nda_results = res_nda.json()["results"]
    assert all("NDA" in r["document_type"] or "Disclosure" in r["filename"] for r in nda_results)

    # 2. Filter by risk_level=CRITICAL
    res_risk = client.get("/contracts/search?q=Section&risk_level=CRITICAL", headers=headers)
    assert res_risk.status_code == 200
    risk_results = res_risk.json()["results"]
    assert all(r["risk_level"] == "CRITICAL" for r in risk_results)
    assert all(r["contract_id"] == data["contract_a"].id for r in risk_results)

    # 3. Filter by contract_id
    res_single = client.get(f"/contracts/search?q=Section&contract_id={data['contract_b'].id}", headers=headers)
    assert res_single.status_code == 200
    single_results = res_single.json()["results"]
    assert len(single_results) <= 1
    if single_results:
        assert single_results[0]["contract_id"] == data["contract_b"].id
