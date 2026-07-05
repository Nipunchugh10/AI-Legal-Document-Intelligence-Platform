"""
Phone Validator Service
-----------------------
Validates and normalizes Indian mobile numbers (+91 prefix followed by 10 digits starting with 6-9).

Day 12 — Phone-Based Two-Factor Authentication
"""

import re
from fastapi import HTTPException, status


def validate_indian_phone(raw_input: str) -> str:
    """
    Strips spaces, dashes, and parentheses from a phone number, validates that
    it is exactly 10 digits after the country code, starts with 6, 7, 8, or 9
    (the only valid starting digits for Indian mobile numbers), and normalizes
    it to E.164 format with the +91 prefix (+91XXXXXXXXXX).

    Raises:
        HTTPException 400 — if the number is not a valid Indian mobile number.
    """
    if not raw_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number cannot be empty.",
        )

    # Strip whitespace, dashes, parens
    cleaned = re.sub(r"[\s\-\(\)]", "", raw_input)

    # Check prefix
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
    elif len(cleaned) == 10:
        digits = cleaned
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid Indian mobile number starting with +91 or a 10-digit number.",
        )

    # Validate that digits is exactly 10 digits and starts with 6, 7, 8, or 9
    if not re.match(r"^[6-9]\d{9}$", digits):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.",
        )

    return f"+91{digits}"
