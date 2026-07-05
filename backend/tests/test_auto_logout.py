"""
Auto-Logout and Inactivity API Integration Tests
------------------------------------------------
Runs a suite of API integration tests for Day 10 auto-logout and cleanup.

To run:
1. Ensure the backend server is running:
   cd backend
   venv\\Scripts\\uvicorn app.main:app --port 8000
2. Execute this script:
   venv\\Scripts\\python tests/test_auto_logout.py
"""

import sys
import os
import random
import string
import requests
from datetime import datetime, timezone, timedelta

# Add backend directory to path so we can import app modules directly in the test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user_session import UserSession
from app.core.security import hash_token
from app.services.session_cleanup import clean_expired_sessions

BASE_URL = "http://localhost:8000"


def generate_random_email():
    """Generate a random email to prevent duplicate registration issues."""
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_logout_{random_str}@example.com"


def run_tests():
    print("=" * 60)
    print(" Running Auto-Logout & Session Cleanup Tests (Day 10)")
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
    user_data = register_response.json()
    print(f"[+] User registered successfully: ID {user_data['id']}")

    # 2. Login to get access token and refresh token
    print("[*] Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    print("[+] Login successful.")

    # 3. Access /auth/me to check active update
    print("[*] Checking initial access to /auth/me...")
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert me_response.status_code == 200, f"Initial /me failed: {me_response.text}"
    
    # 4. Connect to database to verify last_active_at was set
    print("[*] Verifying last_active_at and updating to simulate inactivity...")
    db = SessionLocal()
    try:
        token_hash = hash_token(refresh_token)
        session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
        assert session is not None, "Session record not found in database!"
        print(f"[+] Found session in DB. Last active: {session.last_active_at}")
        
        # Simulate inactivity by setting last_active_at to 45 minutes ago
        simulated_time = datetime.now(timezone.utc) - timedelta(minutes=45)
        session.last_active_at = simulated_time
        db.commit()
        print(f"[+] Simulated inactivity: last_active_at set to {simulated_time}")
    finally:
        db.close()

    # 5. Access /auth/me again (should trigger SESSION_EXPIRED)
    print("[*] Requesting /auth/me after simulated inactivity...")
    expired_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert expired_response.status_code == 401, f"Expected 401 Unauthorized, got {expired_response.status_code}"
    error_detail = expired_response.json().get("detail")
    assert error_detail == "SESSION_EXPIRED", f"Expected 'SESSION_EXPIRED', got '{error_detail}'"
    print("[+] Server correctly rejected the request with 'SESSION_EXPIRED'!")

    # 6. Verify database session is marked is_revoked = True
    print("[*] Verifying database session is revoked after rejection...")
    db = SessionLocal()
    try:
        session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
        assert session.is_revoked is True, "Expected session is_revoked to be True"
        print("[+] Session is successfully marked is_revoked = True in DB.")
    finally:
        db.close()

    # 7. Test background cleanup service
    print("[*] Testing clean_expired_sessions background cleanup function...")
    # Create another session, modify its last_active_at, and run clean_expired_sessions
    print("[*] Logging in user again for cleanup test...")
    login_response2 = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    refresh_token2 = login_response2.json()["refresh_token"]
    
    db = SessionLocal()
    try:
        token_hash2 = hash_token(refresh_token2)
        session2 = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash2).first()
        # Set last_active_at to 45 minutes ago
        session2.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        db.commit()
        
        # Run cleanup
        revoked_count = clean_expired_sessions(db)
        print(f"[+] clean_expired_sessions successfully revoked {revoked_count} session(s).")
        assert revoked_count >= 1
        
        # Re-fetch and check is_revoked
        db.refresh(session2)
        assert session2.is_revoked is True, "Expected session to be revoked by cleanup service"
        print("[+] Cleanup service successfully marked session as is_revoked = True.")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print(" ALL DAY 10 TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[-] TEST FAILURE: {str(ae)}")
    except requests.exceptions.ConnectionError:
        print("\n[-] Error: Could not connect to the API server. Is uvicorn running on http://localhost:8000?")
