"""
Email Two-Factor Authentication (2FA) Login Verification API Integration Tests
-------------------------------------------------------------------------------
Runs a suite of API integration tests for email-based 2FA login flow, resend-otp,
cooldown checks, and attempt limits.

To run:
1. Ensure the backend server is running:
   cd backend
   venv\\Scripts\\uvicorn app.main:app --port 8000
2. Execute this script:
   venv\\Scripts\\python tests/test_phone_2fa_login.py
"""

import sys
import os
import random
import string
import time
import requests
from datetime import datetime, timezone, timedelta

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_otp import EmailOTPVerification
from app.core.security import hash_token

BASE_URL = "http://localhost:8000"


def generate_random_email():
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_email_2fa_{random_str}@example.com"


def run_tests():
    print("=" * 70)
    print(" Running Email 2FA Login Integration Tests")
    print("=" * 70)

    # 1. Register a new user
    email = generate_random_email()
    password = "securePassword123"
    print(f"[*] Registering new user: {email}...")
    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password}
    )
    assert register_response.status_code == 201, f"Registration failed: {register_response.text}"
    user_id = register_response.json()["id"]
    print(f"[+] User registered successfully: ID {user_id}")

    # 2. Verify standard login works when 2FA is not enabled
    print("[*] Performing standard login (2FA disabled)...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    assert login_data["requires_2fa"] is False, "Expected requires_2fa to be False"
    assert "access_token" in login_data and login_data["access_token"] is not None
    assert "refresh_token" in login_data and login_data["refresh_token"] is not None
    print("[+] Standard login verified successfully (no 2FA requirement).")

    # 3. Enable 2FA on the account
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}
    print("[*] Initiating 2FA setup...")
    enable_response = requests.post(
        f"{BASE_URL}/auth/2fa/enable",
        headers=headers
    )
    assert enable_response.status_code == 200, f"Enable 2FA failed: {enable_response.text}"

    # Overwrite the generated OTP hash in DB with a known one for confirmation
    print("[*] Confirming 2FA with OTP code '111111'...")
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
        assert otp_entry is not None, "No OTP verification entry found in DB!"
        otp_entry.otp_hash = hash_token("111111")
        db.commit()
    finally:
        db.close()

    confirm_response = requests.post(
        f"{BASE_URL}/auth/2fa/confirm",
        json={"otp_code": "111111"},
        headers=headers
    )
    assert confirm_response.status_code == 200, f"Confirm 2FA failed: {confirm_response.text}"
    print("[+] Email 2FA activated successfully.")

    # 4. Attempt login with 2FA enabled
    print("[*] Logging in with 2FA enabled...")
    login_2fa_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_2fa_response.status_code == 200, f"2FA login initiation failed: {login_2fa_response.text}"
    login_2fa_data = login_2fa_response.json()
    assert login_2fa_data["requires_2fa"] is True, "Expected requires_2fa to be True"
    assert login_2fa_data["access_token"] is None, "Access token should be null"
    assert login_2fa_data["refresh_token"] is None, "Refresh token should be null"
    pending_token = login_2fa_data["pending_2fa_token"]
    assert pending_token is not None, "Expected pending_2fa_token"
    print(f"[+] 2FA login initiated successfully. Masked message: '{login_2fa_data['message']}'")

    # 5. Verify resend OTP rate limit / cooldown (30 seconds)
    print("[*] Requesting OTP resend immediately (should be rate-limited)...")
    resend_cooldown_response = requests.post(
        f"{BASE_URL}/auth/2fa/resend-otp",
        json={"pending_2fa_token": pending_token}
    )
    assert resend_cooldown_response.status_code == 429, f"Expected 429 rate limit, got {resend_cooldown_response.status_code}"
    print(f"[+] Cooldown rate-limit verified. Response: {resend_cooldown_response.json()['detail']}")

    # 6. Bypass cooldown by modifying DB and testing resend
    print("[*] Overwriting OTP created_at timestamp in DB to bypass cooldown...")
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
        otp_entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=35)
        db.commit()
    finally:
        db.close()

    print("[*] Requesting OTP resend after cooldown period...")
    resend_success_response = requests.post(
        f"{BASE_URL}/auth/2fa/resend-otp",
        json={"pending_2fa_token": pending_token}
    )
    assert resend_success_response.status_code == 200, f"OTP resend failed: {resend_success_response.text}"
    print("[+] Resend OTP successful after cooldown.")

    # 7. Verify attempt limiting (5 attempts)
    print("[*] Verifying attempt limits on invalid code submissions...")
    # Overwrite the newly sent OTP hash to a known one for testing attempts
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
        otp_entry.otp_hash = hash_token("222222")
        otp_entry.attempts = 0
        db.commit()
    finally:
        db.close()

    # Fail 4 times
    for i in range(1, 5):
        verify_fail_resp = requests.post(
            f"{BASE_URL}/auth/2fa/login-verify",
            json={"pending_2fa_token": pending_token, "otp_code": "000000"}
        )
        assert verify_fail_resp.status_code == 400, f"Expected 400, got {verify_fail_resp.status_code}"
        remaining = 5 - i
        assert f"{remaining} attempt(s) remaining" in verify_fail_resp.json()["detail"], "Incorrect remaining attempts message"
        print(f"    - Attempt {i}/5 rejected. Message: '{verify_fail_resp.json()['detail']}'")

    # The 5th fail should lock / invalidate the OTP
    verify_5th_fail_resp = requests.post(
        f"{BASE_URL}/auth/2fa/login-verify",
        json={"pending_2fa_token": pending_token, "otp_code": "000000"}
    )
    assert verify_5th_fail_resp.status_code == 400
    assert "Maximum OTP verification attempts exceeded" in verify_5th_fail_resp.json()["detail"]
    print(f"    - Attempt 5/5 locked out. Message: '{verify_5th_fail_resp.json()['detail']}'")

    # Subsequent attempts should instantly fail with attempt limit message
    verify_extra_fail_resp = requests.post(
        f"{BASE_URL}/auth/2fa/login-verify",
        json={"pending_2fa_token": pending_token, "otp_code": "222222"} # even with correct code
    )
    assert verify_extra_fail_resp.status_code == 400
    assert "Maximum OTP verification attempts exceeded" in verify_extra_fail_resp.json()["detail"]
    print("[+] Attempt limiting verified successfully (locked out after 5 failures).")

    # 8. Reset OTP and verify successful login
    print("[*] Requesting a new OTP to log in successfully...")
    # Bypass cooldown first
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
        otp_entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=35)
        db.commit()
    finally:
        db.close()

    resend_success_response = requests.post(
        f"{BASE_URL}/auth/2fa/resend-otp",
        json={"pending_2fa_token": pending_token}
    )
    assert resend_success_response.status_code == 200

    # Mock the new OTP hash
    db = SessionLocal()
    try:
        otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
        otp_entry.otp_hash = hash_token("333333")
        otp_entry.attempts = 0
        db.commit()
    finally:
        db.close()

    print("[*] Submitting correct OTP '333333' via login-verify...")
    final_login_resp = requests.post(
        f"{BASE_URL}/auth/2fa/login-verify",
        json={"pending_2fa_token": pending_token, "otp_code": "333333"}
    )
    assert final_login_resp.status_code == 200, f"Login verification failed: {final_login_resp.text}"
    final_data = final_login_resp.json()
    assert "access_token" in final_data and final_data["access_token"] is not None
    assert "refresh_token" in final_data and final_data["refresh_token"] is not None
    print("[+] Email 2FA Login verified. Received access + refresh tokens.")

    # 9. Clean up database
    print("[*] Cleaning up test data in database...")
    db = SessionLocal()
    try:
        from app.models.user_session import UserSession
        user_record = db.query(User).filter(User.id == user_id).first()
        if user_record:
            db.query(UserSession).filter(UserSession.user_id == user_id).delete()
            otp_entry = db.query(EmailOTPVerification).filter(EmailOTPVerification.email == email).first()
            if otp_entry:
                db.delete(otp_entry)
            db.delete(user_record)
            db.commit()
            print("[+] Cleanup complete.")
    finally:
        db.close()

    print("\n" + "=" * 70)
    print(" ALL EMAIL 2FA LOGIN INTEGRATION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 70)


if __name__ == "__main__":
    import socket
    import subprocess
    
    def is_port_open(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    server_process = None
    if not is_port_open(8000):
        print("[*] Port 8000 is closed. Starting local Uvicorn server...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        print("[+] Uvicorn server started.")
    else:
        print("[*] Port 8000 is already in use. Assuming backend server is already running.")

    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[-] TEST FAILURE: {str(ae)}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as ce:
        print(f"\n[-] Connection Error: {ce}")
        sys.exit(1)
    finally:
        if server_process:
            print("[*] Stopping local Uvicorn server...")
            server_process.terminate()
            server_process.wait()
            print("[+] Uvicorn server stopped.")
