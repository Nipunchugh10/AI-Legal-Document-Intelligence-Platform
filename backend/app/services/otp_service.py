"""
OTP Service
-----------
Handles generating, sending (via Email / console mock), and verifying 6-digit OTP codes.

Day 14 (Refactored) — Email-Based Two-Factor Authentication
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import hash_token
from app.models.email_otp import EmailOTPVerification

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

settings = get_settings()
logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def send_smtp_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email via standard SMTP if host and credentials are configured.
    Returns True if sent successfully, False otherwise.
    """
    active_settings = get_settings()
    if not active_settings.SMTP_HOST or not active_settings.SMTP_USERNAME:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = active_settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if active_settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(active_settings.SMTP_HOST, active_settings.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(active_settings.SMTP_HOST, active_settings.SMTP_PORT, timeout=10)
            if active_settings.SMTP_USE_TLS:
                server.starttls()

        if active_settings.SMTP_USERNAME and active_settings.SMTP_PASSWORD:
            server.login(active_settings.SMTP_USERNAME, active_settings.SMTP_PASSWORD)

        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully dispatched SMTP email to {to_email}")
        return True
    except Exception as e:
        logger.warning(f"SMTP dispatch to {to_email} failed: {e}. Falling back to mock logger.")
        return False


def generate_otp() -> str:
    """Generate a random 6-digit numeric OTP code."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def send_otp(db: Session, email: str) -> None:
    """
    Generates a 6-digit OTP, hashes it,
    saves it to the database (or updates if an existing pending OTP exists),
    and sends the Email via SMTP if configured, or prints to console mock.
    """
    active_settings = get_settings()
    normalized_email = email.strip().lower()
    code = generate_otp()
    hashed = hash_token(code)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Check if there is an existing verification request for this email
    otp_entry = db.query(EmailOTPVerification).filter(
        EmailOTPVerification.email == normalized_email
    ).first()

    if otp_entry:
        # Reset attempts and update the code hash and expiry
        otp_entry.otp_hash = hashed
        otp_entry.attempts = 0
        otp_entry.expires_at = expires_at
        otp_entry.created_at = now
        otp_entry.is_verified = False
    else:
        otp_entry = EmailOTPVerification(
            email=normalized_email,
            otp_hash=hashed,
            attempts=0,
            expires_at=expires_at,
            is_verified=False
        )
        db.add(otp_entry)

    db.commit()
    db.refresh(otp_entry)

    # Attempt SMTP dispatch if configured
    subject = "Your LegalIntel 2FA Verification Code"
    body = (
        f"Your LegalIntel verification code is: {code}\n\n"
        f"This code will expire in {OTP_EXPIRY_MINUTES} minutes.\n"
        "If you did not request this verification code, please ignore this email or review your account security."
    )

    sent = send_smtp_email(normalized_email, subject, body)
    if not sent:
        # Fallback to console delivery for local development and test environments
        print(f"[EMAIL MOCK] SENT OTP TO {normalized_email}: {code} (Expires in {OTP_EXPIRY_MINUTES} minutes)")
        logger.info(f"OTP dispatched (console mock) to {normalized_email}")



def verify_otp(db: Session, email: str, submitted_code: str) -> bool:
    """
    Verifies the OTP code for the given email.
    Handles expiry, attempt limits, and correct hash verification.

    Raises:
        HTTPException 400 — if the code is incorrect, expired, or has exceeded max attempts.
    """
    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    # Retrieve active OTP verification
    otp_entry = db.query(EmailOTPVerification).filter(
        EmailOTPVerification.email == normalized_email
    ).first()

    if not otp_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP request found for this email address. Please request a new code.",
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
        try:
            from app.core.telemetry import metrics_collector
            metrics_collector.record_auth_failure("expired_otp")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new code.",
        )

    # Verify code hash
    submitted_hash = hash_token(submitted_code)
    if otp_entry.otp_hash != submitted_hash:
        otp_entry.attempts += 1
        db.commit()

        try:
            from app.core.telemetry import metrics_collector
            metrics_collector.record_auth_failure("invalid_otp")
        except Exception:
            pass

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
