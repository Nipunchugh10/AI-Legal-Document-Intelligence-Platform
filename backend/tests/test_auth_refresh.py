"""
Auth Refresh Token and Session API Integration Tests
----------------------------------------------------
Runs a suite of API integration tests for Day 9 refresh token logic.

To run:
1. Ensure the backend server is running:
   cd backend
   venv\\Scripts\\uvicorn app.main:app --port 8000
2. Execute this script:
   venv\\Scripts\\python tests/test_auth_refresh.py
"""

import random
import string
import requests

BASE_URL = "http://localhost:8000"


def generate_random_email():
    """Generate a random email to prevent duplicate registration issues."""
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_session_{random_str}@example.com"


def run_tests():
    print("=" * 60)
    print(" Running Auth Refresh & Session Integration Tests (Day 9)")
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

    # 2. Login to get JWT and Refresh Token
    print("[*] Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    print("[+] Login successful. Access token and Refresh token obtained.")

    # 3. Access /auth/me with access token
    print("[*] Verifying access token with /auth/me...")
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert me_response.status_code == 200, f"Access /me failed: {me_response.text}"
    me_data = me_response.json()
    assert me_data["email"] == email
    print(f"[+] Access token is valid. Email matches: {me_data['email']}")

    # 4. Refresh access token using refresh token
    print("[*] Refreshing access token via /auth/refresh...")
    refresh_response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200, f"Refresh failed: {refresh_response.text}"
    new_token_data = refresh_response.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data
    new_access_token = new_token_data["access_token"]
    new_refresh_token = new_token_data["refresh_token"]
    # Verify that the refresh token rotated
    assert refresh_token != new_refresh_token, "Expected refresh token to rotate"
    print("[+] Token refreshed successfully and rotated.")

    # 5. Access /auth/me with new access token
    print("[*] Verifying new access token with /auth/me...")
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    new_me_response = requests.get(f"{BASE_URL}/auth/me", headers=new_headers)
    assert new_me_response.status_code == 200, f"Access /me with new token failed: {new_me_response.text}"
    print("[+] New access token is valid.")

    # 6. Attempt to refresh with the old refresh token (should fail because it's rotated/revoked)
    print("[*] Verifying old refresh token is invalid (due to rotation)...")
    bad_refresh_response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert bad_refresh_response.status_code == 401, f"Expected 401 for old refresh token, got {bad_refresh_response.status_code}"
    print("[+] Old refresh token rejection verified.")

    # 7. Logout (revoke the current refresh token)
    print("[*] Logging out (revoking the new refresh token)...")
    logout_response = requests.post(
        f"{BASE_URL}/auth/logout",
        json={"refresh_token": new_refresh_token}
    )
    assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
    print("[+] Logout call completed.")

    # 8. Attempt to refresh after logout (should fail)
    print("[*] Verifying refresh token is invalid after logout...")
    post_logout_refresh = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": new_refresh_token}
    )
    assert post_logout_refresh.status_code == 401, f"Expected 401 after logout, got {post_logout_refresh.status_code}"
    print("[+] Revocation verified successfully.")

    print("\n" + "=" * 60)
    print(" ALL DAY 9 TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[-] TEST FAILURE: {str(ae)}")
    except requests.exceptions.ConnectionError:
        print("\n[-] Error: Could not connect to the API server. Is uvicorn running on http://localhost:8000?")
