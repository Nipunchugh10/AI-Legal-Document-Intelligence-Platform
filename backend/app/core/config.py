"""
Core Configuration Module — Day 50: Environment & Secrets Management
-------------------------------------------------------------------
Uses pydantic-settings to load and validate environment configurations
across development, staging, and production environments.

Guarantees:
1. Dynamic environment resolution (loads .env, .env.{APP_ENV}, and .env.local).
2. OS environment variables always take highest priority (12-Factor compliant).
3. Secrets masking in __repr__, __str__, and logging (zero plain secrets in logs).
4. Strict production validation (blocks weak JWT keys, requires DEBUG=False).
5. Comprehensive SMTP credentials management for Email 2FA.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Any, List, Union
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Compute project root (backend/app/core/config.py → project root is 3 levels up)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Set of sensitive field names that MUST never be leaked in string outputs or logs
SENSITIVE_CONFIG_KEYS: set[str] = {
    "JWT_SECRET_KEY",
    "POSTGRES_PASSWORD",
    "GEMINI_API_KEY",
    "LANGCHAIN_API_KEY",
    "GOOGLE_CLIENT_SECRET",
    "SMTP_PASSWORD",
}


def mask_database_url(url: str) -> str:
    """
    Redacts the password component from a database connection string.
    Example:
        postgresql://user:pass@host:5432/db -> postgresql://user:***REDACTED***@host:5432/db
    """
    try:
        parsed = urlsplit(url)
        if parsed.password:
            user = parsed.username or "postgres"
            hostname = parsed.hostname or "localhost"
            netloc = f"{user}:***REDACTED***@{hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        return url
    except Exception:
        return "***REDACTED_URL***"


def normalize_database_url(url: str, enforce_ssl: bool | None = None) -> str:
    """
    Normalizes a database connection URL for SQLAlchemy 2.0 and cloud PostgreSQL providers.

    Features:
    1. Converts legacy 'postgres://' dialect scheme (issued by Neon, Supabase, Render, Heroku)
       to SQLAlchemy 2.0-compliant 'postgresql://'.
       Also converts 'postgres+psycopg2://' to 'postgresql+psycopg2://'.
    2. SSL Mode Enforcement:
       - If enforce_ssl is True: ensures 'sslmode=require' is present in query parameters.
       - If enforce_ssl is None (default): auto-detects remote cloud PostgreSQL hosts.
         Remote hosts (not localhost, 127.0.0.1, 0.0.0.0, postgres, db, test_db)
         automatically receive 'sslmode=require' unless an explicit 'sslmode'
         query parameter is already provided.
       - If enforce_ssl is False: does not auto-inject sslmode.
    3. Serverless / PgBouncer compatibility:
       Preserves existing provider query parameters (e.g. Neon 'endpoint=...', Supabase pooler options).
    4. SQLite & non-postgres schemes:
       Leaves sqlite (e.g. 'sqlite:///:memory:') and other drivers unchanged.
    """
    if not url or not isinstance(url, str):
        return ""

    url_str = url.strip()
    if not url_str:
        return ""

    try:
        parsed = urlsplit(url_str)
        scheme = parsed.scheme.lower()

        # Handle SQLite or other non-postgres schemes
        if scheme.startswith("sqlite"):
            return url_str

        # 1. Normalize dialect scheme
        if scheme == "postgres":
            scheme = "postgresql"
        elif scheme.startswith("postgres+"):
            scheme = "postgresql" + scheme[len("postgres"):]

        # 2. Handle PostgreSQL SSL mode
        if scheme.startswith("postgresql"):
            query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
            hostname = (parsed.hostname or "").lower()

            # Check if host is a local/container development host
            is_local = hostname in {"localhost", "127.0.0.1", "0.0.0.0", "postgres", "db", "test_db", ""}

            should_enforce = enforce_ssl if enforce_ssl is not None else (not is_local)

            if should_enforce and "sslmode" not in query_params:
                query_params["sslmode"] = "require"

            new_query = urlencode(query_params)
            return urlunsplit((scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))

        return url_str
    except Exception:
        return url_str


def resolve_env_files(app_env: str | None = None) -> tuple[str, ...]:
    """
    Resolves existing .env files to load in priority order:
    1. Base: .env (common local defaults)
    2. Specific: .env.{app_env} (e.g. .env.development, .env.staging, .env.production)
    3. Local override: .env.{app_env}.local or .env.local
    Later files override earlier files.
    OS environment variables always override all files.
    """
    if not app_env:
        app_env = os.environ.get("APP_ENV")
        if not app_env:
            # Check if base .env specifies APP_ENV
            base_file = _PROJECT_ROOT / ".env"
            if base_file.exists():
                try:
                    with open(base_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("APP_ENV=") and not line.startswith("#"):
                                app_env = line.split("=", 1)[1].strip().strip("'\"")
                                break
                except Exception:
                    pass
        if not app_env:
            app_env = "development"

    app_env = app_env.lower()
    files: list[str] = []

    # 1. Base .env
    base_file = _PROJECT_ROOT / ".env"
    if base_file.exists():
        files.append(str(base_file))

    # 2. Specific .env.{app_env}
    env_file = _PROJECT_ROOT / f".env.{app_env}"
    if env_file.exists():
        files.append(str(env_file))

    # 3. Local overrides
    local_env_specific = _PROJECT_ROOT / f".env.{app_env}.local"
    local_env_general = _PROJECT_ROOT / ".env.local"
    if local_env_specific.exists():
        files.append(str(local_env_specific))
    elif local_env_general.exists():
        files.append(str(local_env_general))

    return tuple(files)


def load_environment_variables(app_env: str | None = None) -> None:
    """Loads discovered .env files into os.environ for third-party libraries (LangChain, etc.)."""
    for file_path in resolve_env_files(app_env):
        load_dotenv(file_path, override=False)


# Pre-load on import
load_environment_variables()


class Settings(BaseSettings):
    """
    Application settings loaded and validated via pydantic-settings.
    Supports development, staging, production, and test environments.
    """

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5433/legal_ai_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "legal_ai_db"

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 40
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_IDLE_TIMEOUT_MINUTES: int = 40

    # --- SMTP (Email 2FA & Notifications) ---
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@legalintel.ai"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # --- AI / LLM (100% Free Tier Google Gemini) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_FREE_TIER_DAILY_LIMIT: int = 1500
    AI_WARNING_THRESHOLD_PERCENT: float = 80.0

    # --- LangSmith Tracing ---
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ai-legal-document-intelligence"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # --- Vector Database ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # --- Application & Environment Management ---
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    BACKEND_PORT: int = 8000
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://huggingface.co",
        "https://*.hf.space",
    ]
    ALLOWED_HOSTS: Union[List[str], str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "testserver",
        "*.hf.space",
        "huggingface.co",
    ]
    STRICT_SECURITY_HEADERS: bool = False
    SECURE_COOKIES: bool = False
    ALLOW_HF_IFRAME: bool = True

    # --- Rate Limiting (Day 54) ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_2FA_VERIFY: str = "5/minute"
    RATE_LIMIT_2FA_RESEND: str = "3/5minutes"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_STORAGE_URL: str = "memory://"

    # --- OpenTelemetry & Observability (Day 55) ---
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "legal-ai-platform"
    OTEL_SERVICE_VERSION: str = "1.0.0"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    # --- File Upload ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_and_normalize_database_url(cls, v: Any) -> Any:
        """Normalizes postgres:// prefixes to postgresql:// and enforces cloud SSL."""
        if isinstance(v, str) and v.strip():
            return normalize_database_url(v.strip())
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Parses comma-separated string or JSON array into a list of strings."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Any) -> Any:
        """Parses comma-separated string or JSON array into a list of strings."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @model_validator(mode="before")
    @classmethod
    def set_environment_defaults(cls, data: Any) -> Any:
        """
        Applies environment-tailored defaults:
        - Staging / Production: DEBUG=False (unless explicitly passed as True), LOG_LEVEL=INFO, STRICT_SECURITY_HEADERS=True, SECURE_COOKIES=True
        - Development / Test: DEBUG=True, LOG_LEVEL=DEBUG, STRICT_SECURITY_HEADERS=False, SECURE_COOKIES=False
        """
        if isinstance(data, dict):
            env = str(data.get("APP_ENV", "development")).lower()
            if env in {"production", "staging"}:
                # If DEBUG was not explicitly passed as boolean True in kwargs, default to False
                if data.get("DEBUG") is not True:
                    data["DEBUG"] = False

                if data.get("LOG_LEVEL") in {None, "DEBUG"}:
                    data["LOG_LEVEL"] = "INFO"
                data["STRICT_SECURITY_HEADERS"] = True
                data["SECURE_COOKIES"] = True
            elif env in {"development", "test"}:
                data.setdefault("DEBUG", True)
                data.setdefault("LOG_LEVEL", "DEBUG")
                data.setdefault("STRICT_SECURITY_HEADERS", False)
                data.setdefault("SECURE_COOKIES", False)
        return data

    @model_validator(mode="after")
    def validate_environment_integrity(self) -> "Settings":
        """
        Validates environment parameters and enforces strict production security requirements.
        """
        env = self.APP_ENV.lower()
        allowed_envs = {"development", "staging", "production", "test"}
        if env not in allowed_envs:
            raise ValueError(
                f"Invalid APP_ENV '{self.APP_ENV}'. Must be one of: {sorted(allowed_envs)}"
            )

        if env == "production":
            if self.DEBUG:
                raise ValueError("DEBUG cannot be True in production environment.")
            if (
                self.JWT_SECRET_KEY in {
                    "your-super-secret-key-change-this",
                    "changeme",
                    "secret",
                    "",
                }
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Insecure JWT_SECRET_KEY in production! Must be a cryptographically secure key of at least 32 characters."
                )

        return self

    def masked_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation with sensitive credentials and passwords redacted.
        Safe for logging, debugging, and health telemetry.
        """
        data = self.model_dump()
        for key in SENSITIVE_CONFIG_KEYS:
            if key in data and data[key]:
                data[key] = "***REDACTED***"
        if "DATABASE_URL" in data and data["DATABASE_URL"]:
            data["DATABASE_URL"] = mask_database_url(str(data["DATABASE_URL"]))
        return data

    def __repr__(self) -> str:
        """Guarantees that printing Settings never outputs plaintext secrets."""
        masked = self.masked_dict()
        pairs = ", ".join(f"{k}={v!r}" for k, v in masked.items())
        return f"Settings({pairs})"

    def __str__(self) -> str:
        return self.__repr__()


def configure_logging(log_level: str = "INFO") -> None:
    """Configures root logging with the specified log level."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
        logging.getLogger().setLevel(numeric_level)
        return
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Loads settings using discovered .env files for the active APP_ENV.
    """
    load_environment_variables()
    env_files = resolve_env_files()
    if env_files:
        return Settings(_env_file=env_files)
    return Settings()


def reload_settings() -> Settings:
    """
    Clears the LRU cache, re-evaluates environment files,
    and returns a fresh Settings instance.
    """
    get_settings.cache_clear()
    return get_settings()
