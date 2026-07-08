"""
Demo script for Email 2FA verification using bababoiii42@gmail.com
"""

import sys
import os
import requests
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_otp import EmailOTPVerification

BASE_URL = "http://localhost:8000"
EMAIL = "bababoiii42@gmail.com"
PASSWORD = "bababoiiiPassword123"


def clean_existing_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if user:
            print(f"[*] Found existing user {EMAIL}. Cleaning up database for a fresh test...")
            from app.models.user_session import UserSession
            db.query(UserSession).filter(UserSession.user_id == user.id).delete()
            db.query(EmailOTPVerification).filter(EmailOTPVerification.email == EMAIL).delete()
            db.delete(user)
            db.commit()
            print("[+] Cleanup complete.")
    finally:
        db.close()


def run_demo():
    print("=" * 70)
    print(f" Executing Email 2FA Demo for: {EMAIL}")
    print("=" * 70)

    clean_existing_user()

    # Step 1: Register User
    print(f"[*] Step 1: Registering user {EMAIL}...")
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if reg_resp.status_code != 201:
        print(f"[-] Registration failed: {reg_resp.text}")
        return
    print("[+] Registration succeeded!")

    # Step 2: Login to get Access Token
    print("[*] Step 2: Logging in to get access token...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if login_resp.status_code != 200:
        print(f"[-] Login failed: {login_resp.text}")
        return
    login_data = login_resp.json()
    access_token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print("[+] Login succeeded. Obtained access token.")

    # Step 3: Trigger 2FA Enable
    print("[*] Step 3: Requesting to enable 2FA on the account...")
    enable_resp = requests.post(f"{BASE_URL}/auth/2fa/enable", headers=headers)
    if enable_resp.status_code != 200:
        print(f"[-] Enable 2FA failed: {enable_resp.text}")
        return
    print(f"[+] 2FA activation request triggered: {enable_resp.json()['message']}")

    # Step 4: Fetch OTP from Database
    print("[*] Step 4: Fetching the generated OTP from local database (Console Mock)...")
    db = SessionLocal()
    otp_code = None
    try:
        # Since we use bcrypt-style hashing on OTPs in security.py, wait...
        # Wait, do we store the OTP code hash or plaintext in DB?
        # In otp_service.py: `otp_entry.otp_hash = hash_token(code)`
        # Ah! We store the hash in the DB, but the plaintext is printed to the terminal logs!
        # Wait, if we only store the hash, the Python script can't decrypt it to get the plaintext.
        # But wait! We can inspect the backend uvicorn terminal task logs to see what was printed!
        # Or, wait, let's write a small trick: since this is local development, we can check the uvicorn task logs,
        # or we can read the code.
        # Wait, if we need to know the code, does the uvicorn server task log contain it?
        # Yes! Uvicorn prints: `[EMAIL MOCK] SENT OTP TO bababoiii42@gmail.com: 123456`
        # Let's inspect the Uvicorn task logs using Python, or we can look at the task log file!
        # The Uvicorn task ID is 4bc572a6-4a9b-4a9d-bfad-663377255aad/task-361.
        # The log file is at: `C:\Users\Lenovo\.gemini\antigravity-cli\brain\4bc572a6-4a9b-4a9d-bfad-663377255aad\.system_generated\tasks\task-361.log`
        # The Python script can read the log file, parse `[EMAIL MOCK] SENT OTP TO bababoiii42@gmail.com: (\d{6})`, and grab the code!
        # This is incredibly clever! It is a fully automated test loop!
        pass
    finally:
        db.close()

    # Let's sleep 1-2 seconds to allow the log to write
    time.sleep(2)
    
    log_path = r"C:\Users\Lenovo\.gemini\antigravity-cli\brain\4bc572a6-4a9b-4a9d-bfad-663377255aad\.system_generated\tasks\task-361.log"
    import re
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
            matches = re.findall(r"\[EMAIL MOCK\] SENT OTP TO bababoiii42@gmail\.com: (\d{6})", log_content)
            if matches:
                otp_code = matches[-1]
                print(f"[+] Found generated OTP code in backend console logs: {otp_code}")
            else:
                print("[-] Could not parse OTP code from log content. Log content:")
                print(log_content[-500:])
    else:
        print(f"[-] Log file does not exist at: {log_path}")

    if not otp_code:
        print("[-] Verification failed: OTP code not found.")
        return

    # Step 5: Confirm 2FA
    print(f"[*] Step 5: Confirming 2FA with OTP code {otp_code}...")
    confirm_resp = requests.post(f"{BASE_URL}/auth/2fa/confirm", json={"otp_code": otp_code}, headers=headers)
    if confirm_resp.status_code != 200:
        print(f"[-] Confirmation failed: {confirm_resp.text}")
        return
    print(f"[+] 2FA activated: {confirm_resp.json()['message']}")

    # Step 6: Log in again (Must require 2FA)
    print("[*] Step 6: Logging in again (2FA should be required now)...")
    login_2fa_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if login_2fa_resp.status_code != 200:
        print(f"[-] Login failed: {login_2fa_resp.text}")
        return
    login_2fa_data = login_2fa_resp.json()
    assert login_2fa_data["requires_2fa"] is True, "Expected requires_2fa to be True!"
    pending_token = login_2fa_data["pending_2fa_token"]
    print(f"[+] 2FA check works! Received requires_2fa=True and pending token. Message: {login_2fa_data['message']}")

    # Step 7: Retrieve new login OTP from logs
    time.sleep(2)
    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        matches = re.findall(r"\[EMAIL MOCK\] SENT OTP TO bababoiii42@gmail\.com: (\d{6})", log_content)
        if len(matches) >= 2:
            new_otp_code = matches[-1]
            print(f"[+] Found new login OTP code in logs: {new_otp_code}")
        else:
            print("[-] Could not find second OTP code in logs.")
            return

    # Step 8: Verify 2FA code at login
    print(f"[*] Step 8: Submitting OTP {new_otp_code} to /auth/2fa/login-verify...")
    verify_resp = requests.post(
        f"{BASE_URL}/auth/2fa/login-verify",
        json={"pending_2fa_token": pending_token, "otp_code": new_otp_code}
    )
    if verify_resp.status_code != 200:
        print(f"[-] Verification failed: {verify_resp.text}")
        return
    verify_data = verify_resp.json()
    print("[+] Login verification succeeded! Issued access + refresh tokens:")
    print(f"    - Access Token: {verify_data['access_token'][:30]}...")
    print(f"    - Refresh Token: {verify_data['refresh_token'][:30]}...")
    print("\n" + "=" * 70)
    print(" EMAIL 2FA DEMO COMPLETED SUCCESSFULLY! [OK]")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
