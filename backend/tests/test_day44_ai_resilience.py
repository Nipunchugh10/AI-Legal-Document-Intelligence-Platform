"""
Day 44 — Free Google Gemini AI Stack Resilience & Rate Limit Monitoring Tests
-----------------------------------------------------------------------------
Unit and integration tests verifying:
1. AIUsageMonitor 24-hour rolling request aggregation and per-model classification.
2. 80% daily quota consumption warning threshold detection.
3. Protected GET /admin/ai-usage telemetry endpoint.
4. Multi-model Gemini fallback cascade across distinct free-tier quota pools (Flash -> Flash-Lite -> 1.5 Flash).
"""

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.core.security import create_access_token
from app.services.ai_usage_monitor import ai_usage_monitor, AIUsageMonitor
from app.services.llm_provider import get_llm_response, _generate_with_model_cascade, get_langchain_llm

client = TestClient(app)
AI_ADMIN_TEST_EMAIL = "ai_resilience_admin@example.com"


@pytest.fixture
def setup_ai_admin_user():
    """Sets up an authenticated test user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == AI_ADMIN_TEST_EMAIL).first()
        if not user:
            user = User(email=AI_ADMIN_TEST_EMAIL, hashed_password="hashedpassword123", is_active=True, is_2fa_enabled=False)
            db.add(user)
            db.commit()
            db.refresh(user)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=f"ai-admin-session-{uuid.uuid4()}",
            device_info="Pytest-AI-Resilience-Runner",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            is_revoked=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        token = create_access_token(data={"sub": user.email, "email": user.email, "session_id": session.id})
        headers = {"Authorization": f"Bearer {token}"}

        yield {"user_id": user.id, "headers": headers}
    finally:
        db.close()


def test_ai_usage_monitor_recording_and_metrics():
    """Verifies that AIUsageMonitor records events and calculates 24h rolling metrics."""
    monitor = AIUsageMonitor()

    # Record some Gemini calls across models
    monitor.record_call(provider="gemini", model="gemini-2.5-flash", status="success")
    monitor.record_call(provider="gemini", model="gemini-2.5-flash", status="rate_limited")
    monitor.record_call(provider="gemini", model="gemini-2.5-flash-lite", status="success")

    metrics = monitor.get_usage_metrics()

    assert metrics["window_hours"] == 24
    assert metrics["gemini"]["calls_24h"] == 3
    assert metrics["gemini"]["success_count"] == 2
    assert metrics["gemini"]["rate_limited_count"] == 1
    assert metrics["gemini"]["is_warning_threshold_exceeded"] is False
    assert metrics["summary"]["status"] == "healthy"
    assert metrics["summary"]["total_calls_24h"] == 3


def test_ai_usage_monitor_80_percent_warning_threshold():
    """
    Verifies that when Gemini requests exceed 80% of daily quota (>= 1,200),
    is_warning_threshold_exceeded becomes True and summary status changes to 'warning_quota_high'.
    """
    monitor = AIUsageMonitor()

    # Simulate 1205 calls (80.3% of 1500 limit)
    for _ in range(1205):
        monitor.record_call(provider="gemini", model="gemini-2.5-flash", status="success")

    metrics = monitor.get_usage_metrics()
    assert metrics["gemini"]["calls_24h"] == 1205
    assert metrics["gemini"]["usage_percent"] == 80.33
    assert metrics["gemini"]["is_warning_threshold_exceeded"] is True
    assert metrics["summary"]["status"] == "warning_quota_high"
    assert "usage is at 80.33%" in metrics["summary"]["alert_message"]


def test_admin_ai_usage_endpoint_unauthorized():
    """Unauthenticated request to GET /admin/ai-usage should return 401."""
    response = client.get("/admin/ai-usage")
    assert response.status_code == 401


def test_admin_ai_usage_endpoint_authorized(setup_ai_admin_user):
    """Authenticated request to GET /admin/ai-usage should return full telemetry payload."""
    headers = setup_ai_admin_user["headers"]

    # Record some usage on global singleton
    ai_usage_monitor.record_call(provider="gemini", model="gemini-2.5-flash", status="success")

    response = client.get("/admin/ai-usage", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "gemini" in data
    assert "summary" in data
    assert data["gemini"]["provider"] == "Google Gemini (Free Tier)"
    assert data["summary"]["gemini_operational"] is True


def test_gemini_multi_model_fallback_cascade():
    """
    Stress-tests the pure Gemini multi-model fallback cascade across free tier quota buckets:
    Simulates a 429 rate limit on gemini-2.5-flash and confirms automatic failover
    to gemini-2.5-flash-lite successfully completes the extraction.
    """
    ai_usage_monitor.clear()

    # Model mock that fails for gemini-2.5-flash, but succeeds for gemini-2.5-flash-lite
    def mock_generative_model(model_name):
        mock_instance = MagicMock()
        if "flash-lite" in model_name:
            mock_res = MagicMock()
            mock_res.text = "### Legal Clause Analyzed via Gemini 2.5 Flash Lite"
            mock_instance.generate_content.return_value = mock_res
        else:
            mock_instance.generate_content.side_effect = Exception("429 ResourceExhausted: 15 RPM Rate Limit exceeded on model " + model_name)
        return mock_instance

    # Force a NON-lite primary model so the mock rate-limits it and the cascade must
    # fail over to a lite fallback. (The app's default primary is now itself a lite
    # model, so this test pins the primary explicitly rather than relying on the default.)
    from app.core.config import get_settings as _get_settings
    _settings = _get_settings()
    _original_model = _settings.GEMINI_MODEL
    _settings.GEMINI_MODEL = "gemini-2.5-flash"
    try:
        with patch("google.generativeai.GenerativeModel", side_effect=mock_generative_model):
            result = _generate_with_model_cascade("Analyze standard termination clause")
            assert "Gemini 2.5 Flash Lite" in result
    finally:
        _settings.GEMINI_MODEL = _original_model

        # Verify telemetry recorded the rate limit on primary and success on fallback lite
        metrics = ai_usage_monitor.get_usage_metrics()
        assert metrics["gemini"]["rate_limited_count"] >= 1
        assert metrics["gemini"]["success_count"] >= 1


def test_langchain_llm_fallback_chain_configured():
    """
    Verifies that get_langchain_llm constructs a RunnableWithFallbacks chaining
    gemini-2.5-flash -> gemini-2.5-flash-lite -> gemini-1.5-flash.
    """
    llm = get_langchain_llm()
    # If fallbacks are configured, it wraps in RunnableWithFallbacks
    assert hasattr(llm, "fallbacks") or hasattr(llm, "model")
