"""
Active Sessions and Revocation Integration Tests
------------------------------------------------
Tests GET /auth/sessions, DELETE /auth/sessions/{id}, and DELETE /auth/sessions endpoints.
Uses FastAPI TestClient for in-process database state checks.
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
from app.core.security import create_access_token

client = TestClient(app)
TEST_EMAIL = "session_test_user@gmail.com"


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


def setup_test_environment() -> tuple[str, int, int]:
    """Helper to create user and returning authorization headers & primary session IDs."""
    cleanup_db()
    db = SessionLocal()
    try:
        # 1. Create test user
        user = User(
            email=TEST_EMAIL,
            hashed_password="some-hashed-password",
            is_active=True,
            is_2fa_enabled=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 2. Create primary active session
        primary_session = UserSession(
            user_id=user.id,
            refresh_token_hash="primary-hash-123",
            device_info="Primary Test Browser",
            ip_address="127.0.0.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(primary_session)
        db.commit()
        db.refresh(primary_session)

        # 3. Create access token linked to this session
        token = create_access_token(data={"sub": user.email, "session_id": primary_session.id})
        
        return f"Bearer {token}", user.id, primary_session.id
    finally:
        db.close()


def test_get_active_sessions():
    """Verify that we can retrieve active sessions and detect the current one."""
    auth_header, user_id, primary_id = setup_test_environment()
    db = SessionLocal()
    try:
        # Create a second active session
        second_session = UserSession(
            user_id=user_id,
            refresh_token_hash="second-hash-456",
            device_info="Second Device Mobile",
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(second_session)
        db.commit()

        # Call GET /auth/sessions
        headers = {"Authorization": auth_header}
        response = client.get("/auth/sessions", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2

        # Verify attributes and current tagging
        primary_session_item = next(s for s in data if s["id"] == primary_id)
        assert primary_session_item["is_current"] is True
        assert primary_session_item["device_info"] == "Primary Test Browser"

        second_session_item = next(s for s in data if s["id"] == second_session.id)
        assert second_session_item["is_current"] is False
        assert second_session_item["device_info"] == "Second Device Mobile"
    finally:
        db.close()
        cleanup_db()


def test_revoke_specific_session():
    """Verify that we can revoke a specific session (device logout)."""
    auth_header, user_id, primary_id = setup_test_environment()
    db = SessionLocal()
    try:
        # Create secondary session to revoke
        other_session = UserSession(
            user_id=user_id,
            refresh_token_hash="other-hash-789",
            device_info="Other Browser",
            ip_address="10.0.0.2",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(other_session)
        db.commit()
        db.refresh(other_session)

        # Revoke the other session via DELETE /auth/sessions/{id}
        headers = {"Authorization": auth_header}
        response = client.delete(f"/auth/sessions/{other_session.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Check DB status
        db.refresh(other_session)
        assert other_session.is_revoked is True

        # Verify only 1 active session returned now
        sessions_response = client.get("/auth/sessions", headers=headers)
        active_list = sessions_response.json()
        assert len(active_list) == 1
        assert active_list[0]["id"] == primary_id
    finally:
        db.close()
        cleanup_db()


def test_revoke_other_sessions():
    """Verify that we can revoke all other device sessions in bulk."""
    auth_header, user_id, primary_id = setup_test_environment()
    db = SessionLocal()
    try:
        # Create multiple other active sessions
        sess2 = UserSession(
            user_id=user_id,
            refresh_token_hash="hash2",
            device_info="Device 2",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        sess3 = UserSession(
            user_id=user_id,
            refresh_token_hash="hash3",
            device_info="Device 3",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        db.add(sess2)
        db.add(sess3)
        db.commit()

        # Invoke bulk revoke others DELETE /auth/sessions
        headers = {"Authorization": auth_header}
        response = client.delete("/auth/sessions", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify in DB that other sessions are revoked
        db.refresh(sess2)
        db.refresh(sess3)
        assert sess2.is_revoked is True
        assert sess3.is_revoked is True

        # Verify only 1 session (the current one) is still active
        sessions_response = client.get("/auth/sessions", headers=headers)
        active_list = sessions_response.json()
        assert len(active_list) == 1
        assert active_list[0]["id"] == primary_id
    finally:
        db.close()
        cleanup_db()


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Device Session and Revocation Test Suite")
    print("=" * 70)

    try:
        print("[*] Running: test_get_active_sessions...")
        test_get_active_sessions()
        print("[+] Success!")

        print("[*] Running: test_revoke_specific_session...")
        test_revoke_specific_session()
        print("[+] Success!")

        print("[*] Running: test_revoke_other_sessions (bulk)...")
        test_revoke_other_sessions()
        print("[+] Success!")

        cleanup_db()
        print("\n" + "=" * 70)
        print(" ALL DEVICE SESSION TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[-] TEST ASSERTION FAILURE: {e}")
        cleanup_db()
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] TEST ERROR: {e}")
        cleanup_db()
        sys.exit(1)
