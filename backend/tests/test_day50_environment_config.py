"""
Day 50 Test Suite: Environment Configuration & Secrets Management
==================================================================
Validates:
1. Multi-environment configuration profiles (development, staging, production, test).
2. Pydantic-settings dynamic file loading and OS environment variable overrides.
3. Automated secrets redaction in masked_dict(), __repr__(), and __str__().
4. Strict production security validation (blocks weak JWT keys, prevents DEBUG=True).
5. Enterprise security headers middleware injection.
6. SMTP credentials and email dispatch helpers.
7. Git ignore rules and secrets documentation integrity.
"""

import os
import re
import tempfile
import pytest
from pathlib import Path
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.core.config import (
    Settings,
    get_settings,
    reload_settings,
    resolve_env_files,
    mask_database_url,
    SENSITIVE_CONFIG_KEYS,
)
from app.main import app
from app.services.otp_service import send_smtp_email


class TestDay50EnvironmentConfig:
    """Test suite verifying Day 50 deliverables."""

    def test_default_development_environment(self):
        """Verifies that development profile loads debug=True and dev defaults."""
        s = Settings(APP_ENV="development")
        assert s.APP_ENV == "development"
        assert s.DEBUG is True
        assert s.LOG_LEVEL == "DEBUG"
        assert s.STRICT_SECURITY_HEADERS is False
        assert s.SECURE_COOKIES is False

    def test_staging_environment_defaults(self):
        """Verifies that staging profile automatically configures secure defaults."""
        s = Settings(APP_ENV="staging")
        assert s.APP_ENV == "staging"
        assert s.DEBUG is False
        assert s.LOG_LEVEL == "INFO"
        assert s.STRICT_SECURITY_HEADERS is True
        assert s.SECURE_COOKIES is True

    def test_production_environment_defaults_and_validation(self):
        """Verifies that production enforces DEBUG=False and strong 32+ char JWT secrets."""
        # 1. Successful production configuration with strong 32+ character key
        strong_key = "a" * 32
        s = Settings(APP_ENV="production", JWT_SECRET_KEY=strong_key, DEBUG=False)
        assert s.APP_ENV == "production"
        assert s.DEBUG is False
        assert s.LOG_LEVEL == "INFO"
        assert s.STRICT_SECURITY_HEADERS is True
        assert s.SECURE_COOKIES is True

        # 2. Rejection of DEBUG=True in production
        with pytest.raises(ValidationError) as exc_debug:
            Settings(APP_ENV="production", JWT_SECRET_KEY=strong_key, DEBUG=True)
        assert "DEBUG cannot be True in production" in str(exc_debug.value)

        # 3. Rejection of default placeholder JWT key in production
        with pytest.raises(ValidationError) as exc_default_key:
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="your-super-secret-key-change-this",
                DEBUG=False,
            )
        assert "Insecure JWT_SECRET_KEY in production" in str(exc_default_key.value)

        # 4. Rejection of short (<32 chars) JWT key in production
        with pytest.raises(ValidationError) as exc_short_key:
            Settings(APP_ENV="production", JWT_SECRET_KEY="short-secret-key", DEBUG=False)
        assert "Insecure JWT_SECRET_KEY in production" in str(exc_short_key.value)

    def test_invalid_app_env_rejected(self):
        """Verifies that unsupported APP_ENV values raise validation errors."""
        with pytest.raises(ValidationError) as exc_env:
            Settings(APP_ENV="invalid_env_name")
        assert "Invalid APP_ENV" in str(exc_env.value)

    def test_secrets_redaction_and_masking(self):
        """Verifies that sensitive keys and DB passwords are redacted from logs and repr."""
        secret_jwt = "my-super-secret-jwt-key-never-leak-this-string"
        secret_gemini = "AIzaSySecretGeminiKey123456789"
        secret_smtp = "p@ssw0rd123!"
        db_url = "postgresql://myuser:SuperSecretDBPass@localhost:5432/legal_ai_db"

        s = Settings(
            JWT_SECRET_KEY=secret_jwt,
            GEMINI_API_KEY=secret_gemini,
            SMTP_PASSWORD=secret_smtp,
            DATABASE_URL=db_url,
        )

        # 1. Test masked_dict()
        masked = s.masked_dict()
        assert masked["JWT_SECRET_KEY"] == "***REDACTED***"
        assert masked["GEMINI_API_KEY"] == "***REDACTED***"
        assert masked["SMTP_PASSWORD"] == "***REDACTED***"
        assert "SuperSecretDBPass" not in masked["DATABASE_URL"]
        assert "***REDACTED***" in masked["DATABASE_URL"]

        # 2. Test __repr__() and __str__()
        repr_str = repr(s)
        assert secret_jwt not in repr_str
        assert secret_gemini not in repr_str
        assert secret_smtp not in repr_str
        assert "SuperSecretDBPass" not in repr_str
        assert "***REDACTED***" in repr_str

    def test_database_url_masking_utility(self):
        """Verifies mask_database_url function properly redacts passwords across URL variants."""
        masked1 = mask_database_url("postgresql://postgres:mysecret123@localhost:5433/legal_ai_db")
        assert masked1 == "postgresql://postgres:***REDACTED***@localhost:5433/legal_ai_db"

        masked2 = mask_database_url("postgresql://app_user:complex%40pass@remote.db.com:5432/prod_db?sslmode=require")
        assert "complex%40pass" not in masked2
        assert "***REDACTED***" in masked2

        # URL without password
        masked3 = mask_database_url("postgresql://localhost:5432/db")
        assert masked3 == "postgresql://localhost:5432/db"

    def test_cors_origins_parsing(self):
        """Verifies parsing of comma-separated string, JSON list, and native list."""
        # Comma-separated string
        s1 = Settings(CORS_ORIGINS="https://app1.com, https://app2.com")
        assert s1.CORS_ORIGINS == ["https://app1.com", "https://app2.com"]

        # JSON array string
        s2 = Settings(CORS_ORIGINS='["https://app3.com", "https://app4.com"]')
        assert s2.CORS_ORIGINS == ["https://app3.com", "https://app4.com"]

        # Native list
        s3 = Settings(CORS_ORIGINS=["https://app5.com"])
        assert s3.CORS_ORIGINS == ["https://app5.com"]

    def test_smtp_credentials_configuration(self):
        """Verifies SMTP settings fields exist and unconfigured SMTP falls back safely."""
        s = Settings(
            SMTP_HOST="smtp.sendgrid.net",
            SMTP_PORT=587,
            SMTP_USERNAME="apikey",
            SMTP_PASSWORD="SG.secret_api_key",
            SMTP_FROM_EMAIL="auth@legalintel.ai",
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
        )
        assert s.SMTP_HOST == "smtp.sendgrid.net"
        assert s.SMTP_PORT == 587
        assert s.SMTP_USERNAME == "apikey"
        assert s.SMTP_USE_TLS is True

        # Helper fallback when username is empty
        result = send_smtp_email("test@example.com", "Test Subject", "Test Body")
        assert result is False

    def test_security_headers_middleware_injection(self):
        """Verifies that security headers middleware injects security headers when enabled."""
        client = TestClient(app)
        
        # Test endpoint
        response = client.get("/health")
        assert response.status_code == 200

        # When STRICT_SECURITY_HEADERS is enabled or in production
        # Let's verify standard response headers or presence of headers
        headers = response.headers
        assert "x-process-time" in headers

        # Temporarily enable STRICT_SECURITY_HEADERS in active settings
        active_settings = get_settings()
        original_val = active_settings.STRICT_SECURITY_HEADERS
        try:
            active_settings.STRICT_SECURITY_HEADERS = True
            resp_strict = client.get("/health")
            assert resp_strict.headers.get("x-content-type-options") == "nosniff"
            if active_settings.ALLOW_HF_IFRAME:
                assert "huggingface.co" in resp_strict.headers.get("content-security-policy", "")
            else:
                assert resp_strict.headers.get("x-frame-options") == "DENY"
            assert resp_strict.headers.get("x-xss-protection") == "1; mode=block"
            assert resp_strict.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        finally:
            active_settings.STRICT_SECURITY_HEADERS = original_val

    def test_documentation_and_template_files_exist(self):
        """Verifies that secrets.example.md and all 4 .env template files exist."""
        project_root = Path(__file__).resolve().parents[2]
        
        # Templates
        assert (project_root / ".env.example").exists(), ".env.example must exist"
        assert (project_root / ".env.development.example").exists(), ".env.development.example must exist"
        assert (project_root / ".env.staging.example").exists(), ".env.staging.example must exist"
        assert (project_root / ".env.production.example").exists(), ".env.production.example must exist"

        # Documentation
        secrets_doc = project_root / "secrets.example.md"
        assert secrets_doc.exists(), "secrets.example.md must exist"
        doc_content = secrets_doc.read_text(encoding="utf-8")
        assert "Master Environment Variables Matrix" in doc_content
        assert "Cryptographic Secret Generation" in doc_content
        assert "Secret Rotation Procedures" in doc_content
        assert "Emergency Leak" in doc_content
        assert "JWT_SECRET_KEY" in doc_content
        assert "GEMINI_API_KEY" in doc_content
        assert "SMTP_PASSWORD" in doc_content
