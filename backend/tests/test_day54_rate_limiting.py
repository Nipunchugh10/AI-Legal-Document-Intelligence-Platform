"""
Day 54 Test Suite — Hugging Face Spaces Deployment, Iframe Integration & Auth Rate Limiting
==========================================================================================
Validates:
 1. Rate limiting on POST /auth/login (5/min per IP) throttles on 6th attempt with HTTP 429.
 2. Structured HTTP 429 response format (detail, error, Retry-After header).
 3. Rate limiting on POST /auth/register (5/min per IP) throttles on 6th attempt.
 4. Rate limiting on POST /auth/2fa/login-verify (5/min per IP) throttles on 6th attempt.
 5. Rate limiting on POST /auth/2fa/resend-otp (3/5min per IP) throttles on 4th attempt.
 6. Multi-client IP isolation: Throttled Client A does not block independent Client B.
 7. Reverse-proxy client IP extraction from multi-proxy X-Forwarded-For headers.
 8. Fallback client IP extraction from X-Real-IP header.
 9. Rate limiter reset function clears counters and restores access immediately.
10. Dynamic disable/enable toggle allows unlimited requests when disabled.
11. Non-auth endpoints (/health, /health/db) remain unthrottled by auth rate limits.
12. Hugging Face Spaces iframe Content-Security-Policy header configuration.
13. Strict X-Frame-Options DENY fallback when iframe embedding is disabled.
14. Root README.md Hugging Face Spaces YAML frontmatter specification.
"""

import os
import sys
import yaml
import pytest
from pathlib import Path
from fastapi import Request
from fastapi.testclient import TestClient

# Add backend directory to sys.path
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_DIR = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.main import app
from app.core.config import get_settings, reload_settings
from app.core.rate_limit import (
    limiter,
    get_client_ip,
    reset_rate_limits,
    set_rate_limit_enabled,
)


@pytest.fixture(autouse=True)
def cleanup_rate_limits():
    """Ensures a clean rate limiter state before and after each test."""
    reset_rate_limits()
    set_rate_limit_enabled(True)
    yield
    reset_rate_limits()
    set_rate_limit_enabled(True)


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Auth Endpoint Rate Limiting Tests (SlowAPI)
# ==============================================================================

def test_login_rate_limiting_triggers_429(client):
    """Verifies that POST /auth/login allows 5 requests per minute and throttles the 6th."""
    headers = {"X-Forwarded-For": "198.51.100.11"}
    payload = {"email": "nonexistent_user@example.com", "password": "WrongPassword123!"}

    # 1–5: Should be rejected as invalid credentials (401), not rate-limited
    for i in range(5):
        resp = client.post("/auth/login", json=payload, headers=headers)
        assert resp.status_code == 401, f"Attempt {i+1} should return 401 Unauthorized"

    # 6: Should be throttled with HTTP 429 Too Many Requests
    resp_throttled = client.post("/auth/login", json=payload, headers=headers)
    assert resp_throttled.status_code == 429, "6th attempt must be rate-limited to 429"

    data = resp_throttled.json()
    assert "Rate limit exceeded" in data.get("detail", "")
    assert data.get("error") == "rate_limit_exceeded"
    assert "retry-after" in resp_throttled.headers


def test_rate_limit_exceeded_response_format(client):
    """Verifies that 429 responses return consistent JSON error contracts with Retry-After header."""
    headers = {"X-Forwarded-For": "198.51.100.12"}
    payload = {"email": "test_format@example.com", "password": "Password123!"}

    # Exhaust quota (5 requests)
    for _ in range(5):
        client.post("/auth/login", json=payload, headers=headers)

    # 6th request triggers custom handler
    resp = client.post("/auth/login", json=payload, headers=headers)
    assert resp.status_code == 429
    assert resp.headers.get("content-type") == "application/json"
    assert resp.headers.get("retry-after") is not None

    body = resp.json()
    assert "detail" in body
    assert "error" in body
    assert body["error"] == "rate_limit_exceeded"
    assert "Please try again later" in body["detail"]


def test_register_rate_limiting_triggers_429(client):
    """Verifies that POST /auth/register enforces the 5 requests per minute limit."""
    headers = {"X-Forwarded-For": "198.51.100.22"}

    # First 5 registration attempts with valid schema
    for i in range(5):
        payload = {"email": f"reg_attempt_{i}@example.com", "password": "ValidPassword123!"}
        resp = client.post("/auth/register", json=payload, headers=headers)
        assert resp.status_code in (201, 400), f"Attempt {i+1} status: {resp.status_code}"

    # 6th attempt should be blocked by rate limiter
    resp_throttled = client.post(
        "/auth/register",
        json={"email": "reg_throttled@example.com", "password": "ValidPassword123!"},
        headers=headers,
    )
    assert resp_throttled.status_code == 429, "6th registration attempt must be rate-limited"
    assert "rate_limit_exceeded" in resp_throttled.text


def test_2fa_login_verify_rate_limiting_triggers_429(client):
    """Verifies that POST /auth/2fa/login-verify is protected by 5/min rate limit."""
    headers = {"X-Forwarded-For": "198.51.100.33"}
    payload = {"pending_2fa_token": "fake-pending-token", "otp_code": "123456"}

    # First 5 attempts fail with 401 (invalid pending token)
    for i in range(5):
        resp = client.post("/auth/2fa/login-verify", json=payload, headers=headers)
        assert resp.status_code == 401

    # 6th attempt is throttled with 429
    resp_throttled = client.post("/auth/2fa/login-verify", json=payload, headers=headers)
    assert resp_throttled.status_code == 429
    assert resp_throttled.json().get("error") == "rate_limit_exceeded"


def test_2fa_resend_otp_rate_limiting_triggers_429(client):
    """Verifies that POST /auth/2fa/resend-otp is protected by 3/5min rate limit."""
    headers = {"X-Forwarded-For": "198.51.100.44"}
    payload = {"pending_2fa_token": "fake-pending-token"}

    # First 3 attempts fail with 401 (invalid token)
    for i in range(3):
        resp = client.post("/auth/2fa/resend-otp", json=payload, headers=headers)
        assert resp.status_code == 401

    # 4th attempt is throttled with 429 (since limit is 3 per 5 minutes)
    resp_throttled = client.post("/auth/2fa/resend-otp", json=payload, headers=headers)
    assert resp_throttled.status_code == 429
    assert "rate_limit_exceeded" in resp_throttled.text


# ==============================================================================
# 2. Reverse Proxy Client IP Extraction & Multi-Tenant Isolation Tests
# ==============================================================================

def test_ip_isolation_between_clients(client):
    """Verifies that rate limits are isolated per IP and Client B is unaffected by Client A."""
    ip_a = {"X-Forwarded-For": "198.51.100.51"}
    ip_b = {"X-Forwarded-For": "198.51.100.52"}
    payload = {"email": "isolation_test@example.com", "password": "Password123!"}

    # Exhaust Client A's quota
    for _ in range(5):
        client.post("/auth/login", json=payload, headers=ip_a)

    assert client.post("/auth/login", json=payload, headers=ip_a).status_code == 429

    # Client B sends first request: MUST NOT be throttled
    resp_b = client.post("/auth/login", json=payload, headers=ip_b)
    assert resp_b.status_code == 401, "Client B must receive 401 credentials error, not 429"


def test_x_forwarded_for_multiple_proxies_extraction():
    """Verifies that get_client_ip extracts the originating client IP from chained reverse proxies."""
    # Hugging Face Spaces / Cloudflare passes chained proxy IPs: <client>, <hf_proxy>, <internal_lb>
    scope = {
        "type": "http",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.195, 10.0.0.1, 172.16.0.1"),
        ],
    }
    req = Request(scope)
    assert get_client_ip(req) == "203.0.113.195"


def test_x_real_ip_fallback_extraction():
    """Verifies that get_client_ip falls back to X-Real-IP when X-Forwarded-For is absent."""
    scope = {
        "type": "http",
        "headers": [
            (b"x-real-ip", b"198.51.100.77"),
        ],
    }
    req = Request(scope)
    assert get_client_ip(req) == "198.51.100.77"


def test_test_client_ip_override():
    """Verifies that x-test-client-ip header overrides all other IP resolution."""
    scope = {
        "type": "http",
        "headers": [
            (b"x-test-client-ip", b"192.0.2.99"),
            (b"x-forwarded-for", b"203.0.113.10"),
        ],
    }
    req = Request(scope)
    assert get_client_ip(req) == "192.0.2.99"


# ==============================================================================
# 3. Limiter Control & Exemption Tests
# ==============================================================================

def test_reset_rate_limits_clears_counters(client):
    """Verifies that reset_rate_limits() clears in-memory tracking buckets."""
    headers = {"X-Forwarded-For": "198.51.100.88"}
    payload = {"email": "reset_test@example.com", "password": "Password123!"}

    # Exhaust quota
    for _ in range(5):
        client.post("/auth/login", json=payload, headers=headers)
    assert client.post("/auth/login", json=payload, headers=headers).status_code == 429

    # Reset buckets
    reset_rate_limits()

    # Immediate request should succeed past rate limiting
    resp_after_reset = client.post("/auth/login", json=payload, headers=headers)
    assert resp_after_reset.status_code == 401, "After reset, request should return 401, not 429"


def test_set_rate_limit_disabled_allows_unlimited(client):
    """Verifies that disabling the limiter dynamically allows unlimited requests."""
    headers = {"X-Forwarded-For": "198.51.100.99"}
    payload = {"email": "disable_test@example.com", "password": "Password123!"}

    set_rate_limit_enabled(False)

    try:
        # Perform 8 consecutive requests (greater than 5 limit)
        for i in range(8):
            resp = client.post("/auth/login", json=payload, headers=headers)
            assert resp.status_code == 401, f"Attempt {i+1} should not be rate-limited"
    finally:
        set_rate_limit_enabled(True)


def test_unprotected_endpoints_are_not_rate_limited(client):
    """Verifies that non-auth endpoints like /health and /health/db are not throttled."""
    headers = {"X-Forwarded-For": "198.51.100.100"}

    # Repeated health check requests should all return 200
    for _ in range(10):
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200


# ==============================================================================
# 4. Hugging Face Spaces Iframe Embedding & Security Headers Tests
# ==============================================================================

def test_huggingface_iframe_csp_headers(client, monkeypatch):
    """Verifies that responses include Hugging Face iframe CSP frame-ancestors."""
    # Ensure ALLOW_HF_IFRAME is active
    monkeypatch.setenv("SPACE_ID", "test-user/test-space")
    monkeypatch.setenv("APP_ENV", "production")

    resp = client.get("/health")
    assert resp.status_code == 200

    csp = resp.headers.get("content-security-policy", "")
    assert "frame-ancestors" in csp
    assert "https://huggingface.co" in csp
    assert "https://*.huggingface.co" in csp

    # X-Frame-Options: DENY should NOT be present when embedding is permitted
    assert "x-frame-options" not in resp.headers


def test_strict_x_frame_options_when_iframe_disabled(client, monkeypatch):
    """Verifies that X-Frame-Options: DENY is applied when iframe embedding is disabled."""
    from app.core.config import get_settings
    settings = get_settings()

    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("HUGGINGFACE_SPACE", raising=False)
    monkeypatch.setattr(settings, "ALLOW_HF_IFRAME", False)
    monkeypatch.setattr(settings, "STRICT_SECURITY_HEADERS", True)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-frame-options") == "DENY"


# ==============================================================================
# 5. README YAML Frontmatter & Hugging Face Specification Tests
# ==============================================================================

def test_readme_yaml_frontmatter_specification():
    """Verifies that README.md has valid Hugging Face Spaces Docker YAML frontmatter."""
    readme_path = _ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md must exist at project root"

    content = readme_path.read_text(encoding="utf-8")
    assert content.startswith("---"), "README.md must start with YAML frontmatter delimiters"

    # Extract YAML frontmatter block
    parts = content.split("---", 2)
    assert len(parts) >= 3, "README.md frontmatter must be enclosed between '---' delimiters"

    frontmatter_raw = parts[1].strip()
    data = yaml.safe_load(frontmatter_raw)

    assert data.get("title") == "AI Legal Document Intelligence Platform"
    assert data.get("emoji") == "⚖️"
    assert data.get("colorFrom") == "blue"
    assert data.get("sdk") in {"docker", "gradio"}, "Hugging Face Spaces SDK must be 'gradio' or 'docker'"
    if data.get("sdk") == "docker":
        assert data.get("app_port") == 7860, "Hugging Face Spaces app_port must be 7860"
    else:
        assert data.get("app_file") in {"space_app.py", "app.py"}, "Hugging Face Gradio Space must specify app_file"
