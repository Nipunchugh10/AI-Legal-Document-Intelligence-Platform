"""
Chunking and Preprocessing Integration Tests
---------------------------------------------
Tests text cleaning and chunking service functions and the POST /contracts/{id}/chunk endpoint.
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token
from app.services.chunker import clean_text, chunk_text

client = TestClient(app)
TEST_EMAIL = "chunker_test_user@gmail.com"
OTHER_EMAIL = "other_chunker_user@gmail.com"
TEST_TEXT = (
    "This is the header of page 1\n"
    "Page 1 of 3\n"
    "This is the first paragraph. We are discussing legal agreements. It contains important payment terms.\n"
    "\n\n\n"  # excessive newlines
    "This is the second paragraph. Confidentiality clause is here.\n"
    "Confidential\n"  # page marker header
    "2\n"  # page number
    "This is the third paragraph. Liability limits are defined below.\n"
    "Page 3 of 3"
)


def cleanup_test_db():
    db = SessionLocal()
    try:
        for email in [TEST_EMAIL, OTHER_EMAIL]:
            user = db.query(User).filter(User.email == email).first()
            if user:
                db.query(UserSession).filter(UserSession.user_id == user.id).delete()
                contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
                for c in contracts:
                    db.query(Analysis).filter(Analysis.contract_id == c.id).delete()
                    if os.path.exists(c.upload_path):
                        try:
                            os.remove(c.upload_path)
                        except Exception:
                            pass
                db.query(Contract).filter(Contract.user_id == user.id).delete()
                db.delete(user)
                db.commit()
    finally:
        db.close()


def setup_test_db_and_auth() -> tuple[str, int, int]:
    cleanup_test_db()
    
    db = SessionLocal()
    try:
        # Create test user
        user = User(
            email=TEST_EMAIL,
            hashed_password="hashed_password",
            is_active=True,
            is_2fa_enabled=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create another user for isolation tests
        other_user = User(
            email=OTHER_EMAIL,
            hashed_password="hashed_password",
            is_active=True,
            is_2fa_enabled=False
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Create session
        session = UserSession(
            user_id=user.id,
            refresh_token_hash="fake_hash",
            device_info="TestClient",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            is_revoked=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Create contract for main user
        contract = Contract(
            user_id=user.id,
            filename="test_contract.pdf",
            upload_path="fake/path/test_contract.pdf",
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Create contract for other user
        other_contract = Contract(
            user_id=other_user.id,
            filename="other_contract.pdf",
            upload_path="fake/path/other_contract.pdf",
            status="pending"
        )
        db.add(other_contract)
        db.commit()
        db.refresh(other_contract)

        # Generate JWT access token for main user
        token = create_access_token(
            data={"sub": user.email, "session_id": session.id}
        )
        
        return token, contract.id, other_contract.id
    finally:
        db.close()


def test_clean_text_service():
    """Verify that headers, footers, page numbers, and excessive spacing are removed."""
    cleaned = clean_text(TEST_TEXT)
    
    # Assertions
    assert "Page 1 of 3" not in cleaned
    assert "Confidential" not in [line.strip() for line in cleaned.split("\n")]
    assert "\n2\n" not in cleaned
    assert "Page 3 of 3" not in cleaned
    
    # Standard text should be retained
    assert "This is the header of page 1" in cleaned
    assert "This is the first paragraph. We are discussing legal agreements. It contains important payment terms." in cleaned
    assert "This is the second paragraph. Confidentiality clause is here." in cleaned
    assert "This is the third paragraph. Liability limits are defined below." in cleaned
    
    # Triple/excessive newlines should be normalized to double newlines
    assert "\n\n\n" not in cleaned


def test_chunk_text_service():
    """Verify that chunker correctly splits text using token limitations."""
    # Test text that is reasonably long
    long_text = " ".join(["Legal agreement text segment for testing tiktoken chunking."] * 200)
    
    # Split with tiny chunk size to force multiple chunks
    chunks = chunk_text(long_text, chunk_size=50, chunk_overlap=10)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, str)
        assert len(chunk.strip()) > 0


def test_chunk_endpoint_success():
    """Verify standard success flow for chunking endpoint."""
    token, contract_id, _ = setup_test_db_and_auth()
    
    db = SessionLocal()
    try:
        # Pre-seed raw text extraction analysis record
        raw_analysis = Analysis(
            contract_id=contract_id,
            analysis_type="raw_text",
            result_json={
                "text": TEST_TEXT,
                "page_count": 3,
                "is_scanned": False,
                "strategy": "pymupdf"
            }
        )
        db.add(raw_analysis)
        db.commit()
    finally:
        db.close()

    # Call endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"/contracts/{contract_id}/chunk",
        params={"chunk_size": 100, "chunk_overlap": 20},
        headers=headers
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["contract_id"] == contract_id
    assert res_data["chunk_count"] > 0
    assert len(res_data["chunks"]) == res_data["chunk_count"]

    # Verify DB persistence
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "chunks"
        ).first()
        assert analysis is not None
        assert analysis.result_json["chunk_count"] == res_data["chunk_count"]
        assert analysis.result_json["chunk_size"] == 100
        assert analysis.result_json["chunk_overlap"] == 20
        # Ensure chunks don't contain page indicators
        first_chunk = analysis.result_json["chunks"][0]
        assert "Page 1 of 3" not in first_chunk
    finally:
        db.close()
    
    cleanup_test_db()


def test_chunk_endpoint_failures():
    """Verify endpoint error handling states."""
    token, contract_id, other_contract_id = setup_test_db_and_auth()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Accessing other user's contract -> 404
    response = client.post(f"/contracts/{other_contract_id}/chunk", headers=headers)
    assert response.status_code == 404
    assert "Contract not found" in response.json()["detail"]

    # 2. Accessing non-existent contract -> 404
    response = client.post(f"/contracts/999999/chunk", headers=headers)
    assert response.status_code == 404

    # 3. Running chunking before extraction -> 400
    response = client.post(f"/contracts/{contract_id}/chunk", headers=headers)
    assert response.status_code == 400
    assert "must be extracted first" in response.json()["detail"]

    cleanup_test_db()


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Document Chunking and Preprocessing Test Suite")
    print("=" * 70)

    try:
        print("[*] Running: test_clean_text_service...")
        test_clean_text_service()
        print("[+] Success!")

        print("[*] Running: test_chunk_text_service...")
        test_chunk_text_service()
        print("[+] Success!")

        print("[*] Running: test_chunk_endpoint_success...")
        test_chunk_endpoint_success()
        print("[+] Success!")

        print("[*] Running: test_chunk_endpoint_failures...")
        test_chunk_endpoint_failures()
        print("[+] Success!")

        print("\n" + "=" * 70)
        print(" ALL CHUNKING TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        import traceback
        print(f"\n[-] TEST ASSERTION FAILURE:")
        traceback.print_exc()
        cleanup_test_db()
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[-] TEST ERROR:")
        traceback.print_exc()
        cleanup_test_db()
        sys.exit(1)
