"""
Google OAuth Login Integration Tests
-------------------------------------
Tests the /auth/google-login endpoint by mocking the google-auth verification library.
Uses FastAPI TestClient for self-contained, in-process execution.
"""

import sys
import os
from unittest.mock import patch

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession

client = TestClient(app)
TEST_EMAIL = "google_test_user@gmail.com"


def cleanup_db():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            db.query(UserSession).filter(UserSession.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def test_google_login_new_user():
    """Verify that a new Google user is automatically registered and logged in."""
    cleanup_db()

    # Mock payload returned by Google verification
    mock_google_payload = {
        "email": TEST_EMAIL,
        "email_verified": True,
        "sub": "google-oauth2-id-12345",
    }

    # Patch the verify_oauth2_token method inside app.api.auth
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_google_payload):
        response = client.post("/auth/google-login", json={"credential": "mock-google-id-token"})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["requires_2fa"] is False

        # Verify user is created in database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == TEST_EMAIL).first()
            assert user is not None
            assert user.is_active is True
            assert user.is_2fa_enabled is False
        finally:
            db.close()


def test_google_login_existing_user():
    """Verify that an existing user can log in via Google and bypasses 2FA even if enabled."""
    cleanup_db()

    # Pre-create user with 2FA enabled
    db = SessionLocal()
    try:
        user = User(
            email=TEST_EMAIL,
            hashed_password="some-hashed-password",
            is_active=True,
            is_2fa_enabled=True,  # 2FA active
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    mock_google_payload = {
        "email": TEST_EMAIL,
        "email_verified": True,
        "sub": "google-oauth2-id-12345",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_google_payload):
        response = client.post("/auth/google-login", json={"credential": "mock-google-id-token"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Google user must bypass the 2FA prompt
        assert data["requires_2fa"] is False


def test_google_login_invalid_token():
    """Verify that an invalid Google token is rejected with 401 Unauthorized."""
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Invalid token")):
        response = client.post("/auth/google-login", json={"credential": "invalid-token"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid Google credential token"


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Google OAuth Test Suite via TestClient")
    print("=" * 70)
    
    try:
        print("[*] Running: test_google_login_new_user...")
        test_google_login_new_user()
        print("[+] Success!")

        print("[*] Running: test_google_login_existing_user (2FA bypass)...")
        test_google_login_existing_user()
        print("[+] Success!")

        print("[*] Running: test_google_login_invalid_token...")
        test_google_login_invalid_token()
        print("[+] Success!")

        cleanup_db()
        print("\n" + "=" * 70)
        print(" ALL GOOGLE OAUTH TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[-] TEST ASSERTION FAILURE: {e}")
        cleanup_db()
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] TEST ERROR: {e}")
        cleanup_db()
        sys.exit(1)
