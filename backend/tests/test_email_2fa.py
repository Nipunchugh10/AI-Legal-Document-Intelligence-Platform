"""
Email-Based 2FA Integration Tests
---------------------------------
Tests enabling, confirming, login-verifying, and disabling Email 2FA.
Uses a brute-force approach to locate the plaintext OTP from database hashes during tests.
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
from app.models.email_otp import EmailOTPVerification
from app.core.security import create_access_token, hash_token

client = TestClient(app)
TEST_EMAIL = "2fa_test_user@gmail.com"
TEST_PASSWORD = "securePassword123"


def cleanup_db():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            db.query(EmailOTPVerification).filter(EmailOTPVerification.email == TEST_EMAIL).delete()
            db.query(UserSession).filter(UserSession.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def setup_test_user():
    cleanup_db()
    db = SessionLocal()
    try:
        # Create test user with 2FA initially disabled
        from app.core.security import hash_password
        user = User(
            email=TEST_EMAIL,
            hashed_password=hash_password(TEST_PASSWORD),
            is_active=True,
            is_2fa_enabled=False
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def find_otp_code_from_db() -> str:
    """Brute force the 6-digit OTP code using the hash saved in the database."""
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(
            EmailOTPVerification.email == TEST_EMAIL
        ).first()
        if not otp_entry:
            raise Exception("No OTP entry found in database!")
        
        target_hash = otp_entry.otp_hash
        for i in range(1000000):
            candidate = f"{i:06d}"
            if hash_token(candidate) == target_hash:
                return candidate
        raise Exception("Failed to brute-force OTP code hash!")
    finally:
        db.close()


def test_2fa_flow():
    setup_test_user()

    # 1. Step A: Login without 2FA
    print("[*] Testing login with 2FA disabled...")
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    login_data = response.json()
    assert login_data["requires_2fa"] is False
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    auth_headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    # 2. Step B: Trigger 2FA setup
    print("[*] Triggering 2FA setup...")
    enable_res = client.post("/auth/2fa/enable", headers=auth_headers)
    assert enable_res.status_code == 200
    assert enable_res.json()["status"] == "success"

    # 3. Step C: Confirm 2FA setup with correct OTP
    print("[*] Confirming 2FA activation...")
    code = find_otp_code_from_db()
    confirm_res = client.post(
        "/auth/2fa/confirm",
        headers=auth_headers,
        json={"otp_code": code}
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "success"

    # Verify user record updated in database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        assert user.is_2fa_enabled is True
    finally:
        db.close()

    # 4. Step D: Login again with 2FA enabled
    print("[*] Testing login with 2FA enabled (expecting 2FA prompt)...")
    response_2fa = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response_2fa.status_code == 200
    login_data_2fa = response_2fa.json()
    assert login_data_2fa["requires_2fa"] is True
    assert login_data_2fa.get("pending_2fa_token") is not None
    assert login_data_2fa.get("access_token") is None
    assert login_data_2fa.get("refresh_token") is None
    pending_token = login_data_2fa["pending_2fa_token"]

    # 5. Step E: Verify 2FA at login
    print("[*] Performing 2FA verification on login...")
    login_code = find_otp_code_from_db()
    verify_res = client.post(
        "/auth/2fa/login-verify",
        json={"pending_2fa_token": pending_token, "otp_code": login_code}
    )
    assert verify_res.status_code == 200
    tokens = verify_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    active_auth = {"Authorization": f"Bearer {tokens['access_token']}"}

    # 6. Step F: Disable 2FA
    print("[*] Disabling 2FA...")
    disable_res = client.post("/auth/2fa/disable", headers=active_auth)
    assert disable_res.status_code == 200
    assert disable_res.json()["status"] == "success"

    # Verify 2FA status is False in database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        assert user.is_2fa_enabled is False
    finally:
        db.close()

    cleanup_db()


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Email 2FA Integration Test Suite")
    print("=" * 70)

    test_2fa_flow()
    print("\n" + "=" * 70)
    print(" ALL EMAIL 2FA TESTS PASSED! [OK]")
    print("=" * 70)
