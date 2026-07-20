"""
PDF Extraction Integration Tests
--------------------------------
Tests PDF text extraction service functions and the POST /contracts/{id}/extract endpoint.
Creates a real PDF file with text dynamically using PyMuPDF to avoid mock fragility.
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fitz  # PyMuPDF
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token
from app.services.pdf_extractor import (
    extract_with_pymupdf,
    extract_with_pdfplumber,
    extract_pdf_text
)

client = TestClient(app)
TEST_EMAIL = "pdf_test_user@gmail.com"
OTHER_EMAIL = "other_pdf_user@gmail.com"
SAMPLE_PDF_PATH = "test_sample_document.pdf"
SAMPLE_SCANNED_PDF_PATH = "test_scanned_document.pdf"
TEST_TEXT = "This is a sample contract text for testing PDF extraction logic. Indemnity and liability clauses."


@pytest.fixture(autouse=True, scope="module")
def setup_module_test_pdfs():
    create_test_pdfs()
    yield
    cleanup_test_files_and_db()


def create_test_pdfs():
    """Generates real PDF files using PyMuPDF to use during tests."""
    # 1. Text-based PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), TEST_TEXT)
    doc.save(SAMPLE_PDF_PATH)
    doc.close()

    # 2. Scanned-like PDF (page has no text)
    doc_scanned = fitz.open()
    doc_scanned.new_page()  # Blank page, no text inserted
    doc_scanned.save(SAMPLE_SCANNED_PDF_PATH)
    doc_scanned.close()


def cleanup_test_files_and_db():
    # Remove files
    for path in [SAMPLE_PDF_PATH, SAMPLE_SCANNED_PDF_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    # DB cleanup
    db = SessionLocal()
    try:
        for email in [TEST_EMAIL, OTHER_EMAIL]:
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Delete user sessions first
                db.query(UserSession).filter(UserSession.user_id == user.id).delete()
                
                # Delete analyses and contracts
                contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
                for c in contracts:
                    db.query(Analysis).filter(Analysis.contract_id == c.id).delete()
                    # Remove file on disk if any
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
    cleanup_test_files_and_db()
    create_test_pdfs()
    
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

        # Create user session in database
        session = UserSession(
            user_id=user.id,
            refresh_token_hash="hash-pdf-123",
            device_info="Test PDF Extractor",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Create contract record pointing to our sample PDF
        contract = Contract(
            user_id=user.id,
            filename="test_sample_document.pdf",
            upload_path=os.path.abspath(SAMPLE_PDF_PATH),
            status="pending"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Create access token
        token = create_access_token(data={"sub": user.email, "session_id": session.id})
        auth_header = f"Bearer {token}"

        return auth_header, user.id, contract.id
    finally:
        db.close()


def test_pymupdf_extraction():
    """Verify PyMuPDF strategy extracts correct text and page count."""
    text, page_count = extract_with_pymupdf(SAMPLE_PDF_PATH)
    assert page_count == 1
    assert TEST_TEXT in text


def test_pdfplumber_extraction():
    """Verify pdfplumber strategy extracts correct text and page count."""
    text, page_count = extract_with_pdfplumber(SAMPLE_PDF_PATH)
    assert page_count == 1
    assert TEST_TEXT in text


def test_scanned_pdf_detection():
    """Verify that density logic flags a blank/scanned PDF."""
    result = extract_pdf_text(SAMPLE_SCANNED_PDF_PATH)
    assert result["is_scanned"] is True
    assert result["page_count"] == 1


def test_text_pdf_detection():
    """Verify that a text PDF is not marked as scanned."""
    result = extract_pdf_text(SAMPLE_PDF_PATH)
    assert result["is_scanned"] is False
    assert TEST_TEXT in result["text"]


def test_extract_endpoint_success():
    """Verify POST /contracts/{id}/extract endpoint executes successfully and updates DB status."""
    auth_header, user_id, contract_id = setup_test_db_and_auth()

    headers = {"Authorization": auth_header}
    response = client.post(
        f"/contracts/{contract_id}/extract?strategy=pymupdf",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == contract_id
    assert data["page_count"] == 1
    assert data["is_scanned"] is False
    assert data["strategy"] == "pymupdf"
    assert TEST_TEXT in data["text"]

    # Verify status in database changed to 'ingested'
    db = SessionLocal()
    try:
        updated_contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert updated_contract.status == "ingested"

        # Verify Analysis entry was written
        analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "raw_text"
        ).first()
        assert analysis is not None
        assert analysis.result_json["is_scanned"] is False
        assert TEST_TEXT in analysis.result_json["text"]
    finally:
        db.close()


def test_extract_endpoint_unauthorized():
    """Verify that another user cannot trigger extraction of a contract."""
    auth_header, user_id, contract_id = setup_test_db_and_auth()

    # Create another user and token
    db = SessionLocal()
    other_id = None
    try:
        other_user = User(
            email=OTHER_EMAIL,
            hashed_password="hashed_password",
            is_active=True,
            is_2fa_enabled=False
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        other_id = other_user.id

        session = UserSession(
            user_id=other_user.id,
            refresh_token_hash="hash-pdf-456",
            device_info="Other Extractor",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        token = create_access_token(data={"sub": other_user.email, "session_id": session.id})
        other_auth = f"Bearer {token}"
    finally:
        db.close()

    try:
        headers = {"Authorization": other_auth}
        response = client.post(
            f"/contracts/{contract_id}/extract",
            headers=headers
        )
        assert response.status_code == 404
    finally:
        # Clean up second user
        db = SessionLocal()
        try:
            if other_id:
                # Delete user sessions first
                db.query(UserSession).filter(UserSession.user_id == other_id).delete()
                u = db.query(User).filter(User.id == other_id).first()
                if u:
                    db.delete(u)
                    db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    print("=" * 70)
    print(" Running PDF Text Extractor Test Suite")
    print("=" * 70)

    try:
        create_test_pdfs()

        print("[*] Running: test_pymupdf_extraction...")
        test_pymupdf_extraction()
        print("[+] Success!")

        print("[*] Running: test_pdfplumber_extraction...")
        test_pdfplumber_extraction()
        print("[+] Success!")

        print("[*] Running: test_scanned_pdf_detection...")
        test_scanned_pdf_detection()
        print("[+] Success!")

        print("[*] Running: test_text_pdf_detection...")
        test_text_pdf_detection()
        print("[+] Success!")

        print("[*] Running: test_extract_endpoint_success...")
        test_extract_endpoint_success()
        print("[+] Success!")

        print("[*] Running: test_extract_endpoint_unauthorized...")
        test_extract_endpoint_unauthorized()
        print("[+] Success!")

        cleanup_test_files_and_db()
        print("\n" + "=" * 70)
        print(" ALL PDF EXTRACTION TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[-] TEST ASSERTION FAILURE: {e}")
        cleanup_test_files_and_db()
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] TEST ERROR: {e}")
        cleanup_test_files_and_db()
        sys.exit(1)
