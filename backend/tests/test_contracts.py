"""
Contract Upload and Management API Integration Tests
---------------------------------------------------
Runs a suite of API integration tests against a running server.

To run:
1. Ensure the backend server is running:
   cd backend
   venv\\Scripts\\uvicorn app.main:app --port 8000
2. Execute this script:
   venv\\Scripts\\python tests/test_contracts.py
"""

import os
import random
import string
import requests
import io

BASE_URL = "http://localhost:8000"


def generate_random_email():
    """Generate a unique random email to prevent duplicate registration errors."""
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_{random_str}@example.com"


def run_tests():
    print("=" * 60)
    print(" Running Contract API Integration Tests")
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

    # 2. Login to get JWT
    print("[*] Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token_data = login_response.json()
    token = token_data["access_token"]
    print("[+] Login successful, JWT obtained.")

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Test Invalid File Extension (Upload TXT instead of PDF)
    print("[*] Testing file type validation (uploading invalid TXT file)...")
    invalid_file = io.BytesIO(b"Hello world, this is a plain text file, not a PDF.")
    files = {"file": ("test_contract.txt", invalid_file, "text/plain")}
    upload_response = requests.post(
        f"{BASE_URL}/contracts/upload",
        headers=headers,
        files=files
    )
    assert upload_response.status_code == 400, f"Expected 400 Bad Request, got {upload_response.status_code}: {upload_response.text}"
    print(f"[+] Validation works: Rejected invalid file extension with: {upload_response.json()['detail']}")

    # 4. Test Valid PDF Upload
    print("[*] Testing valid PDF upload...")
    # Create a dummy PDF content (just enough to pass extension check and represent PDF bytes)
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    pdf_file = io.BytesIO(dummy_pdf_content)
    files = {"file": ("employment_agreement.pdf", pdf_file, "application/pdf")}
    upload_response = requests.post(
        f"{BASE_URL}/contracts/upload",
        headers=headers,
        files=files
    )
    assert upload_response.status_code == 201, f"Upload failed: {upload_response.text}"
    contract_data = upload_response.json()
    contract_id = contract_data["id"]
    print(f"[+] Contract uploaded successfully: ID {contract_id}, Filename: {contract_data['filename']}")
    assert contract_data["filename"] == "employment_agreement.pdf"
    assert contract_data["status"] == "pending"
    assert os.path.exists(contract_data["upload_path"]), "Uploaded file does not exist on disk!"

    # 5. Test File Size Limit (Upload dummy file > 10MB)
    print("[*] Testing file size validation (uploading large 11MB file)...")
    large_pdf_content = b"%PDF-1.4\n" + (b"A" * (11 * 1024 * 1024))
    large_pdf_file = io.BytesIO(large_pdf_content)
    files = {"file": ("large_contract.pdf", large_pdf_file, "application/pdf")}
    upload_response = requests.post(
        f"{BASE_URL}/contracts/upload",
        headers=headers,
        files=files
    )
    assert upload_response.status_code == 413, f"Expected 413 Entity Too Large, got {upload_response.status_code}: {upload_response.text}"
    print(f"[+] Validation works: Rejected oversized file with: {upload_response.json()['detail']}")

    # 6. List User's Contracts
    print("[*] Fetching user's contract list...")
    list_response = requests.get(f"{BASE_URL}/contracts/", headers=headers)
    assert list_response.status_code == 200, f"Listing failed: {list_response.text}"
    contracts_list = list_response.json()
    print(f"[+] Found {len(contracts_list)} contracts for user.")
    assert len(contracts_list) >= 1
    assert any(c["id"] == contract_id for c in contracts_list)

    # 7. Get Single Contract Details
    print(f"[*] Fetching contract details for ID {contract_id}...")
    detail_response = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=headers)
    assert detail_response.status_code == 200, f"Detail lookup failed: {detail_response.text}"
    detail_data = detail_response.json()
    assert detail_data["id"] == contract_id
    assert detail_data["filename"] == "employment_agreement.pdf"
    print(f"[+] Retreived correct details for contract ID {contract_id}.")

    # 8. Test Data Isolation (Unauthorized lookup of this contract using a different user)
    print("[*] Testing data isolation (unauthorized access check)...")
    other_email = generate_random_email()
    print(f"[*] Registering second user: {other_email}...")
    other_register = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": other_email, "password": password}
    )
    assert other_register.status_code == 201
    other_login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": other_email, "password": password}
    )
    other_token = other_login.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempt to look up the first user's contract
    bad_detail = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=other_headers)
    assert bad_detail.status_code == 404, f"Expected 404 Not Found for unauthorized lookup, got {bad_detail.status_code}: {bad_detail.text}"
    print("[+] Data isolation verified: Second user cannot see first user's contract details.")

    # Clean up the uploaded dummy contract file
    if os.path.exists(contract_data["upload_path"]):
        os.remove(contract_data["upload_path"])
        print("[+] Cleaned up local test file.")

    print("\n" + "=" * 60)
    print(" ALL TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[-] TEST FAILURE: {str(ae)}")
    except requests.exceptions.ConnectionError:
        print("\n[-] Error: Could not connect to the API server. Is uvicorn running on http://localhost:8000?")
