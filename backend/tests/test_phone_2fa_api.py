"""
Phone Two-Factor Authentication (2FA) API Integration Tests
-----------------------------------------------------------
Runs a suite of API integration tests for Day 12 2FA phone registration and OTP verification.

To run:
1. Ensure the backend server is running:
   cd backend
   venv\\Scripts\\uvicorn app.main:app --port 8000
2. Execute this script:
   venv\\Scripts\\python tests/test_phone_2fa_api.py
"""

import sys
import os
import random
import string
import requests
from datetime import datetime, timezone, timedelta

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.phone_otp import PhoneOTPVerification
from app.core.security import hash_token

BASE_URL = "http://localhost:8000"


def generate_random_email():
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_2fa_{random_str}@example.com"


def generate_random_phone():
    start_digit = random.choice(["6", "7", "8", "9"])
    rest_digits = "".join(random.choices(string.digits, k=9))
    return f"+91{start_digit}{rest_digits}"


def run_tests():
    print("=" * 60)
    print(" Running Phone 2FA API Integration Tests (Day 12)")
    print("=" * 60)

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

    # 2. Login to get access token
    print("[*] Logging in to get access token...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print("[+] Login successful.")

    # 3. Request add-phone with invalid number (non-Indian)
    print("[*] Requesting add-phone with invalid country code...")
    invalid_response = requests.post(
        f"{BASE_URL}/auth/2fa/add-phone",
        json={"phone_number": "+12025550143"},
        headers=headers
    )
    # Pydantic validation error or HTTP 400
    assert invalid_response.status_code in (400, 422), f"Expected 400 or 422, got {invalid_response.status_code}: {invalid_response.text}"
    print("[+] Invalid phone format correctly rejected by server.")

    # 4. Request add-phone with valid Indian number
    phone = generate_random_phone()
    print(f"[*] Requesting add-phone with valid phone number: {phone}...")
    add_response = requests.post(
        f"{BASE_URL}/auth/2fa/add-phone",
        json={"phone_number": phone},
        headers=headers
    )
    assert add_response.status_code == 200, f"Add phone failed: {add_response.text}"
    print(f"[+] Add-phone successful. Server response: {add_response.json()['message']}")

    # Check user record in DB has phone number set, but is_phone_verified is still False
    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.id == user_id).first()
        assert user_record.phone_number == phone, "Phone number was not set on the user!"
        assert user_record.is_phone_verified is False, "User phone should not be verified yet!"
        print("[+] DB state verified: phone number set, verification is False.")

        # 5. Overwrite the generated OTP hash with a known one for confirmation test
        print("[*] Overwriting generated OTP hash in DB with known hash for code '123456'...")
        otp_hash = hash_token("123456")
        otp_entry = db.query(PhoneOTPVerification).filter(PhoneOTPVerification.phone_number == phone).first()
        assert otp_entry is not None, "No OTP verification entry found in DB!"
        otp_entry.otp_hash = otp_hash
        db.commit()
        print("[+] OTP hash updated in DB.")
    finally:
        db.close()

    # 6. Request confirm-phone with wrong code (should fail)
    print("[*] Confirming phone with incorrect OTP code...")
    wrong_confirm_response = requests.post(
        f"{BASE_URL}/auth/2fa/confirm-phone",
        json={"phone_number": phone, "otp_code": "000000"},
        headers=headers
    )
    assert wrong_confirm_response.status_code == 400, f"Expected 400, got {wrong_confirm_response.status_code}: {wrong_confirm_response.text}"
    print(f"[+] Incorrect OTP correctly rejected. Server message: {wrong_confirm_response.json()['detail']}")

    # 7. Request confirm-phone with correct code (should succeed)
    print("[*] Confirming phone with correct OTP code '123456'...")
    confirm_response = requests.post(
        f"{BASE_URL}/auth/2fa/confirm-phone",
        json={"phone_number": phone, "otp_code": "123456"},
        headers=headers
    )
    assert confirm_response.status_code == 200, f"Confirm phone failed: {confirm_response.text}"
    print(f"[+] Confirm-phone successful. Server response: {confirm_response.json()['message']}")

    # 8. Check user record in DB again
    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.id == user_id).first()
        assert user_record.is_phone_verified is True, "User phone should now be marked verified!"
        print("[+] DB state verified: is_phone_verified is now True.")
        
        # Clean up test user sessions, otp entries, and finally the user
        from app.models.user_session import UserSession
        db.query(UserSession).filter(UserSession.user_id == user_id).delete()
        otp_entry = db.query(PhoneOTPVerification).filter(PhoneOTPVerification.phone_number == phone).first()
        if otp_entry:
            db.delete(otp_entry)
        db.delete(user_record)
        db.commit()
        print("[+] Database cleaned up.")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print(" ALL PHONE 2FA API TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[-] TEST FAILURE: {str(ae)}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n[-] Error: Could not connect to the API server. Is uvicorn running on http://localhost:8000?")
        sys.exit(1)
