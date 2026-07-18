"""
Core Configuration Module
-------------------------
Uses pydantic-settings to load and validate all environment variables
from a .env file at the project root.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Compute the absolute path to the project root .env file
# config.py is at: backend/app/core/config.py → project root is 3 levels up
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Database ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/legal_ai_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "legal_ai_db"

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 40
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_IDLE_TIMEOUT_MINUTES: int = 40

    # --- SMTP (Email 2FA) — configured when moving to production ---
    # SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
    # (Currently using console mock for local development)

    # --- AI / LLM (Google Gemini) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # --- Vector Database ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # --- Application ---
    APP_ENV: str = "development"
    DEBUG: bool = True
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # --- File Upload ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    The lru_cache ensures the .env file is only read once per process.
    """
    return Settings()
