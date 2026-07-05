"""
Phone OTP Database Schema and Model Integration Tests
------------------------------------------------------
Verifies that User and PhoneOTPVerification SQLAlchemy models work with
the database schema, and validates the Pydantic schemas.

To run:
venv\\Scripts\\python tests/test_phone_otp_schema.py
"""

import sys
import os
import random
import string
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.phone_otp import PhoneOTPVerification
from app.schemas.auth import OTPRequest, OTPVerifyRequest


def generate_random_email():
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_otp_{random_str}@example.com"


def generate_random_phone():
    # Generate a random valid Indian phone number (+91 followed by 6-9, then 9 digits)
    start_digit = random.choice(["6", "7", "8", "9"])
    rest_digits = "".join(random.choices(string.digits, k=9))
    return f"+91{start_digit}{rest_digits}"


def test_pydantic_schemas():
    print("[*] Testing Pydantic OTP schemas...")
    
    # 1. Test valid Indian phone number
    valid_phone = "+919876543210"
    otp_req = OTPRequest(phone_number=valid_phone)
    assert otp_req.phone_number == valid_phone
    print("  [+] Valid OTPRequest passed validation.")

    # 2. Test invalid country code
    try:
        OTPRequest(phone_number="+19876543210")
        assert False, "Should have failed on invalid country code"
    except ValidationError as e:
        print("  [+] Invalid country code correctly rejected.")

    # 3. Test invalid starting digit for Indian number (needs to start with 6-9)
    try:
        OTPRequest(phone_number="+915876543210")
        assert False, "Should have failed on starting digit 5"
    except ValidationError as e:
        print("  [+] Invalid starting digit correctly rejected.")

    # 4. Test invalid length
    try:
        OTPRequest(phone_number="+91987654321")
        assert False, "Should have failed on short number"
    except ValidationError as e:
        print("  [+] Too short number correctly rejected.")

    # 5. Test valid OTPVerifyRequest
    verify_req = OTPVerifyRequest(phone_number=valid_phone, otp_code="123456")
    assert verify_req.phone_number == valid_phone
    assert verify_req.otp_code == "123456"
    print("  [+] Valid OTPVerifyRequest passed validation.")

    # 6. Test invalid non-digit OTP code
    try:
        OTPVerifyRequest(phone_number=valid_phone, otp_code="123a56")
        assert False, "Should have failed on non-digit OTP"
    except ValidationError as e:
        print("  [+] Non-digit OTP correctly rejected.")

    # 7. Test invalid OTP length
    try:
        OTPVerifyRequest(phone_number=valid_phone, otp_code="12345")
        assert False, "Should have failed on short OTP"
    except ValidationError as e:
        print("  [+] Short OTP correctly rejected.")


def test_db_operations():
    print("[*] Testing Database operations for phone models...")
    db = SessionLocal()
    try:
        # 1. Create a user with a phone number
        email = generate_random_email()
        phone = generate_random_phone()
        print(f"  [*] Creating test user with email={email}, phone={phone}...")
        
        user = User(
            email=email,
            hashed_password="hashedpassword123",
            phone_number=phone,
            is_phone_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.phone_number == phone
        assert user.is_phone_verified is False
        print("  [+] Test user saved and verified in DB.")

        # 2. Update user's is_phone_verified to True
        user.is_phone_verified = True
        db.commit()
        db.refresh(user)
        assert user.is_phone_verified is True
        print("  [+] Test user phone verification status successfully updated to True.")

        # 3. Create a PhoneOTPVerification entry
        otp_hash = "f6e0a1e2c289f2db4811df6b696f8c67c5147814b7e8d649db3ad42548482928"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        print(f"  [*] Creating PhoneOTPVerification for phone={phone}...")
        
        otp_entry = PhoneOTPVerification(
            phone_number=phone,
            otp_hash=otp_hash,
            attempts=0,
            expires_at=expires_at,
            is_verified=False
        )
        db.add(otp_entry)
        db.commit()
        db.refresh(otp_entry)

        assert otp_entry.id is not None
        assert otp_entry.phone_number == phone
        assert otp_entry.otp_hash == otp_hash
        assert otp_entry.attempts == 0
        assert otp_entry.is_verified is False
        print("  [+] PhoneOTPVerification saved and verified in DB.")

        # 4. Clean up the database records
        db.delete(otp_entry)
        db.delete(user)
        db.commit()
        print("  [+] Cleanup of database records completed.")

    finally:
        db.close()


def run_tests():
    print("=" * 60)
    print(" Running Day 12 Phone OTP Integration Tests")
    print("=" * 60)
    test_pydantic_schemas()
    test_db_operations()
    print("=" * 60)
    print(" ALL DAY 12 TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[-] TEST FAILURE: {str(e)}")
        sys.exit(1)
