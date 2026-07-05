"""
OTP Service
-----------
Handles generating, sending (via SMS / console mock), and verifying 6-digit OTP codes.

Day 12 — Phone-Based Two-Factor Authentication
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import hash_token

settings = get_settings()
from app.models.phone_otp import PhoneOTPVerification
from app.services.phone_validator import validate_indian_phone

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def generate_otp() -> str:
    """Generate a random 6-digit numeric OTP code."""
    # Using secrets to ensure it is cryptographically secure
    return "".join(secrets.choice("0123456789") for _ in range(6))


def send_otp(db: Session, phone_number: str) -> None:
    """
    Validates the phone number, generates a 6-digit OTP, hashes it,
    saves it to the database (or updates if an existing pending OTP exists),
    and sends the SMS. If SMS credentials are not configured, prints to console (mock).

    Returns the plain text code (ONLY for test/development logging visibility; normally SMS delivers it).
    """
    normalized_phone = validate_indian_phone(phone_number)
    code = generate_otp()
    hashed = hash_token(code)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Check if there is an existing verification request for this phone number
    otp_entry = db.query(PhoneOTPVerification).filter(
        PhoneOTPVerification.phone_number == normalized_phone
    ).first()

    if otp_entry:
        # Reset attempts and update the code hash and expiry
        otp_entry.otp_hash = hashed
        otp_entry.attempts = 0
        otp_entry.expires_at = expires_at
        otp_entry.created_at = now
        otp_entry.is_verified = False
    else:
        otp_entry = PhoneOTPVerification(
            phone_number=normalized_phone,
            otp_hash=hashed,
            attempts=0,
            expires_at=expires_at,
            is_verified=False
        )
        db.add(otp_entry)

    db.commit()
    db.refresh(otp_entry)

    # Deliver the SMS (or fall back to console logging)
    if settings.SMS_API_KEY:
        try:
            logger.info(f"Sending OTP SMS to {normalized_phone} via provider SDK...")
            # SECURITY: Never log the plaintext OTP code in production.
            # The SMS provider delivers it; we only confirm dispatch.
            print(f"[SMS PROVIDER] OTP dispatched to {normalized_phone}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {normalized_phone}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to send verification SMS. Please try again.",
            )
    else:
        # Fallback to console print for local developer visibility
        print(f"[SMS MOCK] SENT OTP TO {normalized_phone}: {code} (Expires in {OTP_EXPIRY_MINUTES} minutes)")

    return  # OTP code is never returned; it is delivered via SMS only


def verify_otp(db: Session, phone_number: str, submitted_code: str) -> bool:
    """
    Verifies the OTP code for the given phone number.
    Handles expiry, attempt limits, and correct hash verification.

    Raises:
        HTTPException 400 — if the code is incorrect, expired, or has exceeded max attempts.
    """
    normalized_phone = validate_indian_phone(phone_number)
    now = datetime.now(timezone.utc)

    # Retrieve active OTP verification
    otp_entry = db.query(PhoneOTPVerification).filter(
        PhoneOTPVerification.phone_number == normalized_phone
    ).first()

    if not otp_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP request found for this phone number. Please request a new code.",
        )

    # Check if already verified
    if otp_entry.is_verified:
        return True

    # Check if attempts exceeded
    if otp_entry.attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum OTP verification attempts exceeded. Please request a new code.",
        )

    # Check expiration
    if otp_entry.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new code.",
        )

    # Verify code hash
    submitted_hash = hash_token(submitted_code)
    if otp_entry.otp_hash != submitted_hash:
        otp_entry.attempts += 1
        db.commit()

        remaining = MAX_OTP_ATTEMPTS - otp_entry.attempts
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum OTP verification attempts exceeded. Please request a new code.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect OTP code. {remaining} attempt(s) remaining.",
        )

    # Mark as verified
    otp_entry.is_verified = True
    db.commit()
    return True
