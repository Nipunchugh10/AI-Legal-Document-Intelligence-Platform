"""
Ingestion Pipeline Integration Tests
------------------------------------
Tests the end-to-end ingestion pipeline service and the POST /contracts/{id}/ingest endpoint (sync and async).
"""

import sys
import os
import shutil
import time
import fitz  # PyMuPDF
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token
from app.core.config import get_settings
from app.services.vector_store import get_vector_store_service

client = TestClient(app)
TEST_EMAIL = "ingest_test_user@gmail.com"
OTHER_EMAIL = "other_ingest_user@gmail.com"
TEST_PDF_PATH = "test_ingestion_doc.pdf"
TEST_CHROMA_DIR = "./test_ingestion_chroma"
TEST_TEXT = "This is the first page of the freelance contract. Payment terms are INR 50,000. Confidentiality is required."

def setup_test_environment() -> tuple[str, int, int]:
    # Set ChromaDB persist directory to test folder
    settings = get_settings()
    settings.CHROMA_PERSIST_DIR = TEST_CHROMA_DIR
    if os.path.exists(TEST_CHROMA_DIR):
        try:
            shutil.rmtree(TEST_CHROMA_DIR)
        except Exception as e:
            print(f"\n[!] Note: Could not completely remove setup test directory {TEST_CHROMA_DIR} due to file locks: {e}")

    # Clean up test files
    if os.path.exists(TEST_PDF_PATH):
        os.remove(TEST_PDF_PATH)

    # Generate a real PDF file
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), TEST_TEXT)
    doc.save(TEST_PDF_PATH)
    doc.close()

    # Clear DB tables for these test users
    db = SessionLocal()
    try:
        for email in [TEST_EMAIL, OTHER_EMAIL]:
            user = db.query(User).filter(User.email == email).first()
            if user:
                db.query(UserSession).filter(UserSession.user_id == user.id).delete()
                contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
                for c in contracts:
                    db.query(Analysis).filter(Analysis.contract_id == c.id).delete()
                db.query(Contract).filter(Contract.user_id == user.id).delete()
                db.delete(user)
                db.commit()

        # Create test users
        user = User(email=TEST_EMAIL, hashed_password="hashed_password", is_active=True, is_2fa_enabled=False)
        db.add(user)
        other_user = User(email=OTHER_EMAIL, hashed_password="hashed_password", is_active=True, is_2fa_enabled=False)
        db.add(other_user)
        db.commit()
        db.refresh(user)
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

        # Create contract for main user pointing to real test PDF
        contract = Contract(
            user_id=user.id,
            filename="test_ingestion_doc.pdf",
            upload_path=os.path.abspath(TEST_PDF_PATH),
            status="pending"
        )
        db.add(contract)

        # Create contract for other user
        other_contract = Contract(
            user_id=other_user.id,
            filename="other_doc.pdf",
            upload_path="fake/path.pdf",
            status="pending"
        )
        db.add(other_contract)

        db.commit()
        db.refresh(contract)
        db.refresh(other_contract)

        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        return token, contract.id, other_contract.id
    finally:
        db.close()

def cleanup_test_environment():
    if os.path.exists(TEST_PDF_PATH):
        os.remove(TEST_PDF_PATH)
    
    # Safely clear ChromaDB test directory
    if os.path.exists(TEST_CHROMA_DIR):
        try:
            shutil.rmtree(TEST_CHROMA_DIR)
        except Exception as e:
            print(f"\n[!] Note: Could not completely remove test directory {TEST_CHROMA_DIR} due to file locks: {e}")

    # Final DB cleanup
    db = SessionLocal()
    try:
        for email in [TEST_EMAIL, OTHER_EMAIL]:
            user = db.query(User).filter(User.email == email).first()
            if user:
                db.query(UserSession).filter(UserSession.user_id == user.id).delete()
                contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
                for c in contracts:
                    db.query(Analysis).filter(Analysis.contract_id == c.id).delete()
                db.query(Contract).filter(Contract.user_id == user.id).delete()
                db.delete(user)
                db.commit()
    finally:
        db.close()


def test_ingest_endpoint_sync_success():
    """Verify synchronous end-to-end ingestion pipeline endpoint executes correctly."""
    token, contract_id, _ = setup_test_environment()
    headers = {"Authorization": f"Bearer {token}"}

    # Run ingestion synchronously
    response = client.post(
        f"/contracts/{contract_id}/ingest",
        params={"background": False},
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ingested"

    # Verify DB persistence of analyses records
    db = SessionLocal()
    try:
        # Check raw text record
        raw_text_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "raw_text"
        ).first()
        assert raw_text_analysis is not None
        assert "Payment terms" in raw_text_analysis.result_json["text"]

        # Check chunks record
        chunks_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "chunks"
        ).first()
        assert chunks_analysis is not None
        assert chunks_analysis.result_json["chunk_count"] > 0

        # Verify Vector Store (ChromaDB) contains the chunks
        vector_store = get_vector_store_service()
        vector_store.settings.CHROMA_PERSIST_DIR = TEST_CHROMA_DIR
        query_results = vector_store.query_contract_chunks(
            contract_id=contract_id,
            query_text="Confidentiality INR 50,000",
            n_results=1
        )
        assert len(query_results) == 1
        assert "INR 50,000" in query_results[0]["text"]
    finally:
        db.close()


def test_ingest_endpoint_async_success():
    """Verify asynchronous (background task) end-to-end ingestion works."""
    token, contract_id, _ = setup_test_environment()
    headers = {"Authorization": f"Bearer {token}"}

    # Run ingestion asynchronously (background=True is default)
    response = client.post(
        f"/contracts/{contract_id}/ingest",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    # Poll status until it transitions to 'ingested' (max 10 seconds)
    db = SessionLocal()
    try:
        completed = False
        for _ in range(20):
            time.sleep(0.5)
            # Re-fetch from DB
            db.expire_all()
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if contract.status == "ingested":
                completed = True
                break
            elif contract.status == "failed":
                break
        
        assert completed, "Background ingestion task timed out or failed."
    finally:
        db.close()


def test_ingest_endpoint_failures():
    """Verify ingestion pipeline endpoint error handling."""
    token, contract_id, other_contract_id = setup_test_environment()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Accessing other user's contract -> 404
    response = client.post(
        f"/contracts/{other_contract_id}/ingest",
        params={"background": False},
        headers=headers
    )
    assert response.status_code == 404

    # 2. Accessing non-existent contract -> 404
    response = client.post(
        f"/contracts/999999/ingest",
        params={"background": False},
        headers=headers
    )
    assert response.status_code == 404


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Ingestion Pipeline Integration Test Suite")
    print("=" * 70)

    try:
        print("[*] Running: test_ingest_endpoint_sync_success...")
        test_ingest_endpoint_sync_success()
        print("[+] Success!")

        print("[*] Running: test_ingest_endpoint_async_success...")
        test_ingest_endpoint_async_success()
        print("[+] Success!")

        print("[*] Running: test_ingest_endpoint_failures...")
        test_ingest_endpoint_failures()
        print("[+] Success!")

        cleanup_test_environment()
        print("\n" + "=" * 70)
        print(" ALL INGESTION PIPELINE TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        import traceback
        print(f"\n[-] TEST ASSERTION FAILURE:")
        traceback.print_exc()
        cleanup_test_environment()
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[-] TEST ERROR:")
        traceback.print_exc()
        cleanup_test_environment()
        sys.exit(1)
