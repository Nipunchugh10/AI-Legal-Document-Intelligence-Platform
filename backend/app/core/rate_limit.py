"""
Rate Limiting Subsystem
-----------------------
Enterprise rate limiting using slowapi for sensitive authentication and security endpoints.
Protects against brute-force credential stuffing, OTP enumeration, and endpoint abuse.

Day 54 — Hugging Face Spaces Deployment, Iframe Integration & Auth Rate Limiting
"""

import os
import logging
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_client_ip(request: Request) -> str:
    """
    Extracts the originating client IP address for accurate rate limiting.

    Priority:
    1. 'x-test-client-ip' header: Explicit test IP override for automated test suites.
    2. 'x-forwarded-for' header: Standard reverse-proxy header populated by Hugging Face Spaces,
       Cloudflare, AWS ALB, and Docker networks. The first comma-separated address is the client.
    3. 'x-real-ip' header: Nginx/HAProxy direct upstream client IP header.
    4. FastAPI TestClient scoping: If running under FastAPI TestClient ('testclient') during pytest,
       isolates the bucket per test function node to prevent cross-test bucket contamination
       while preserving intra-test threshold validation.
    5. 'request.client.host': Direct socket connection client IP.
    6. Fallback default: '127.0.0.1'.
    """
    if not request:
        return "127.0.0.1"

    # 1. Test header override
    test_ip = request.headers.get("x-test-client-ip")
    if test_ip:
        return test_ip.strip()

    # 2. X-Forwarded-For (Hugging Face Spaces & Reverse Proxies)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    # 3. X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # 4. FastAPI TestClient scoping during automated test runs
    if request.client and request.client.host == "testclient":
        current_test = os.environ.get("PYTEST_CURRENT_TEST")
        if current_test:
            test_name = current_test.split(" ")[0].split("::")[-1]
            return f"testclient_{test_name}"
        return "testclient"

    # 5. Direct socket client host
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


# Initialize the Limiter singleton with in-memory or Redis storage
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
)


def custom_rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom HTTP 429 Too Many Requests exception handler.
    Returns standard API error JSON containing 'detail' and 'error' keys,
    along with standard 'Retry-After' response header.
    """
    retry_after = "60"
    detail_msg = f"Rate limit exceeded: {exc.detail}. Please try again later."

    logger.warning(
        "Rate limit exceeded for IP %s on %s %s: %s",
        get_client_ip(request),
        request.method,
        request.url.path,
        exc.detail,
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": detail_msg,
            "error": "rate_limit_exceeded",
        },
        headers={
            "Retry-After": retry_after,
        },
    )


def reset_rate_limits() -> None:
    """Clears in-memory rate limiter tracking buckets. Useful for test teardown."""
    try:
        limiter.reset()
    except Exception as exc:
        logger.debug("Failed to reset rate limiter storage: %s", exc)


def set_rate_limit_enabled(enabled: bool) -> None:
    """Dynamically enables or disables rate limiting."""
    limiter.enabled = enabled
