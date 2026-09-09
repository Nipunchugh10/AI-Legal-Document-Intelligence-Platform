"""
Day 52 Test Suite — Cloud Database Setup for Hugging Face Spaces
================================================================
Comprehensive verification for managed cloud PostgreSQL setup, connection URL
normalization, SSL mode enforcement, serverless connection pooling resilience,
active database health probes, schema verification, and Alembic sync.

Test Coverage:
 1. Scheme Normalization: postgres:// -> postgresql:// conversion
 2. Dialect Preservation: postgresql:// and postgresql+psycopg2:// preservation
 3. Driver Preservation: SQLite (sqlite:///:memory:) handling
 4. Cloud SSL Enforcement: auto-injects sslmode=require for remote cloud endpoints
 5. SSL Preservation: respects pre-existing sslmode query parameters (verify-full, etc.)
 6. Local Exemption: does not force sslmode for localhost, 127.0.0.1, postgres docker network
 7. Serverless Support: handles Neon serverless pooler endpoints & parameter preservation
 8. Pydantic Settings Validation: DATABASE_URL validator normalizes inputs transparently
 9. Secrets Masking: credentials and passwords redacted from URLs and error traces
10. Engine Configuration: verifies pool_pre_ping=True, pool_recycle, and pool sizing
11. Live Health Probe: check_database_connection() against active test PostgreSQL
12. Target URL Probe: check_database_connection() with custom URLs and SQLite
13. Diagnostic Fault Isolation: unreachable connection fails gracefully with masked errors
14. Schema Integrity: all 8 core tables, relations, and retention columns exist
15. Alembic Head Sync: database revision matches migration heads
16. Programmatic Verification: run_verification() execution and JSON payload
17. CLI Subprocess Verification: scripts/verify_cloud_db.py --json execution
18. API Health Endpoints: GET /health/db and GET /admin/db-health
"""

import sys
import os
import json
import subprocess
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

# Add backend directory to path
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.main import app
from app.core.config import (
    get_settings,
    normalize_database_url,
    mask_database_url,
    Settings,
)
from app.core.database import (
    engine,
    check_database_connection,
    CORE_TABLES,
    SessionLocal,
)
from app.core.security import create_access_token, hash_password, create_refresh_token
from app.models.user import User
from scripts.verify_cloud_db import get_alembic_heads, run_verification


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    user = db_session.query(User).filter_by(email="day52_tester@legalai.com").first()
    if not user:
        user = User(
            email="day52_tester@legalai.com",
            hashed_password=hash_password("Day52SecurePass!2026"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, db_session):
    _, session_id = create_refresh_token(user_id=test_user.id, db=db_session)
    token = create_access_token(data={"sub": test_user.email, "session_id": session_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# 1. URL Normalization & Scheme Tests
# ==============================================================================

def test_normalize_postgres_scheme_conversion():
    """Verifies that postgres:// is converted to postgresql:// for SQLAlchemy 2.0."""
    url = "postgres://usr:pwd@localhost:5432/mydb"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql://")
    assert "postgres://" not in normalized
    assert "usr:pwd@localhost:5432/mydb" in normalized


def test_normalize_postgres_plus_driver_conversion():
    """Verifies that postgres+psycopg2:// is converted to postgresql+psycopg2://."""
    url = "postgres+psycopg2://usr:pwd@localhost:5432/mydb"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+psycopg2://")


def test_normalize_preserves_postgresql_and_sqlite():
    """Verifies that valid postgresql:// and sqlite:// URLs are preserved intact."""
    pg_url = "postgresql://usr:pwd@localhost:5432/mydb"
    assert normalize_database_url(pg_url) == pg_url

    sqlite_mem = "sqlite:///:memory:"
    assert normalize_database_url(sqlite_mem) == sqlite_mem

    sqlite_file = "sqlite:///./test.db"
    assert normalize_database_url(sqlite_file) == sqlite_file


def test_normalize_handles_empty_or_invalid():
    """Verifies edge cases for empty or non-string inputs."""
    assert normalize_database_url("") == ""
    assert normalize_database_url("   ") == ""
    assert normalize_database_url(None) == ""


# ==============================================================================
# 2. SSL Mode Enforcement Tests
# ==============================================================================

def test_normalize_ssl_enforcement_remote_hosts():
    """Verifies that remote cloud database endpoints automatically receive sslmode=require."""
    neon_url = "postgres://alex:secret@ep-cool-feather-123456.us-east-2.aws.neon.tech/neondb"
    normalized = normalize_database_url(neon_url)
    assert normalized.startswith("postgresql://")
    assert "sslmode=require" in normalized

    supabase_url = "postgresql://postgres:secret@db.abcxyz.supabase.co:5432/postgres"
    norm_supabase = normalize_database_url(supabase_url)
    assert "sslmode=require" in norm_supabase


def test_normalize_ssl_preserves_existing_sslmode():
    """Verifies that pre-existing sslmode parameters are never overwritten."""
    url_full = "postgresql://usr:pwd@ep-test.neon.tech/db?sslmode=verify-full&other=1"
    normalized = normalize_database_url(url_full)
    assert "sslmode=verify-full" in normalized
    assert "sslmode=require" not in normalized

    url_disabled = "postgresql://usr:pwd@remote-host.com/db?sslmode=disable"
    norm_disabled = normalize_database_url(url_disabled)
    assert "sslmode=disable" in norm_disabled


def test_normalize_ssl_local_hosts_exemption():
    """Verifies that local development hosts are exempted from auto-SSL injection."""
    for host in ["localhost:5432", "127.0.0.1:5432", "0.0.0.0:5432", "postgres:5432", "db:5432"]:
        local_url = f"postgresql://usr:pwd@{host}/mydb"
        normalized = normalize_database_url(local_url)
        assert "sslmode" not in normalized

    # When enforce_ssl is explicitly requested
    enforced = normalize_database_url("postgresql://usr:pwd@localhost:5432/mydb", enforce_ssl=True)
    assert "sslmode=require" in enforced

    # When enforce_ssl is explicitly False
    unenforced = normalize_database_url("postgresql://usr:pwd@neon.tech/mydb", enforce_ssl=False)
    assert "sslmode" not in unenforced


def test_normalize_serverless_neon_pooler_urls():
    """Verifies handling of Neon serverless connection pooler endpoints."""
    neon_pooled = (
        "postgres://user:pass@ep-gentle-lake-123-pooler.eu-central-1.aws.neon.tech:5432/neondb"
        "?sslmode=require&endpoint=ep-gentle-lake-123-pooler"
    )
    norm_pooled = normalize_database_url(neon_pooled)
    assert norm_pooled.startswith("postgresql://")
    assert "-pooler.eu-central-1.aws.neon.tech" in norm_pooled
    assert "sslmode=require" in norm_pooled
    assert "endpoint=ep-gentle-lake-123-pooler" in norm_pooled


# ==============================================================================
# 3. Settings & Credentials Masking Tests
# ==============================================================================

def test_settings_database_url_validation():
    """Verifies that Pydantic Settings model automatically normalizes DATABASE_URL."""
    cloud_raw = "postgres://db_user:db_pass@ep-test.us-west-2.aws.neon.tech/legal_prod"
    cfg = Settings(DATABASE_URL=cloud_raw)
    assert cfg.DATABASE_URL.startswith("postgresql://")
    assert "sslmode=require" in cfg.DATABASE_URL


def test_mask_database_url_redacts_credentials_safely():
    """Verifies that mask_database_url hides passwords while preserving host, port, and query params."""
    plain = "postgresql://myuser:supersecretpass@db.example.com:5432/mydb?sslmode=require"
    masked = mask_database_url(plain)
    assert "supersecretpass" not in masked
    assert "***REDACTED***" in masked
    assert "myuser" in masked
    assert "db.example.com:5432" in masked
    assert "sslmode=require" in masked

    # Passwordless and sqlite preservation
    assert mask_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


# ==============================================================================
# 4. Engine & Pooling Resilience Tests
# ==============================================================================

def test_engine_configuration_and_resilience():
    """Verifies that the SQLAlchemy engine is configured with resilient pooling options."""
    assert engine.pool is not None
    # Pre-ping is vital for serverless databases (Neon, Supabase)
    assert engine.pool._pre_ping is True
    # Pool recycle is set to prevent stale socket EOF
    assert engine.pool._recycle == 1800


# ==============================================================================
# 5. Database Diagnostic & Health Probes
# ==============================================================================

def test_check_database_connection_live_success():
    """Verifies check_database_connection() against the active test database."""
    diag = check_database_connection()
    assert diag["status"] == "connected"
    assert diag["dialect"] == "postgresql"
    assert diag["version"] is not None
    assert "PostgreSQL" in diag["version"]
    assert isinstance(diag["latency_ms"], float)
    assert diag["latency_ms"] >= 0.0
    assert diag["tables_count"] >= 8
    assert diag["core_tables_healthy"] is True
    assert diag["missing_tables"] == []
    assert diag["error"] is None
    assert diag["alembic_version"] is not None


def test_check_database_connection_with_target_url():
    """Verifies probe against custom targets including SQLite in-memory."""
    sqlite_diag = check_database_connection(target_url="sqlite:///:memory:")
    assert sqlite_diag["status"] == "connected"
    assert sqlite_diag["dialect"] == "sqlite"
    assert sqlite_diag["core_tables_healthy"] is False  # Empty in-memory DB lacks core tables
    assert len(sqlite_diag["missing_tables"]) == len(CORE_TABLES)


def test_check_database_connection_failure_isolation():
    """Verifies that an unreachable host fails gracefully without leaking credentials."""
    unreachable_url = "postgresql://user:mypassword123@127.0.0.1:5499/nonexistent_db"
    diag = check_database_connection(target_url=unreachable_url, timeout=1.0)
    assert diag["status"] == "error"
    assert "mypassword123" not in str(diag["error"])
    assert diag["core_tables_healthy"] is False
    assert diag["version"] is None


# ==============================================================================
# 6. Schema & Alembic Integrity Tests
# ==============================================================================

def test_schema_integrity_all_core_tables_and_columns():
    """Verifies that all 8 core tables exist and required columns are present."""
    insp = inspect(engine)
    db_tables = set(insp.get_table_names())

    for table_name in CORE_TABLES:
        assert table_name in db_tables, f"Core table {table_name} missing from database"

    # Verify users table specific columns (including Day 48 data_retention_days)
    user_columns = {col["name"] for col in insp.get_columns("users")}
    assert "id" in user_columns
    assert "email" in user_columns
    assert "hashed_password" in user_columns
    assert "data_retention_days" in user_columns


def test_alembic_migration_head_is_synced():
    """Verifies that the database Alembic revision matches the repository migration head."""
    heads = get_alembic_heads()
    assert len(heads) == 1
    expected_head = heads[0]

    with engine.connect() as conn:
        actual_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert actual_rev == expected_head


# ==============================================================================
# 7. Verification Script Tests
# ==============================================================================

def test_verify_cloud_db_programmatic_execution():
    """Verifies programmatic execution of run_verification()."""
    exit_code, diag = run_verification(json_output=True)
    assert exit_code == 0
    assert diag["status"] == "connected"
    assert diag["core_tables_healthy"] is True
    assert diag["target_url_masked"] is not None
    assert "***REDACTED***" in diag["target_url_masked"] or "@" in diag["target_url_masked"]


def test_verify_cloud_db_cli_invocation():
    """Verifies CLI subprocess invocation of backend/scripts/verify_cloud_db.py."""
    script_path = _BACKEND_DIR / "scripts" / "verify_cloud_db.py"
    cmd = [sys.executable, str(script_path), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "connected"
    assert data["core_tables_healthy"] is True


# ==============================================================================
# 8. API Health Endpoints
# ==============================================================================

def test_api_system_health(client):
    """Verifies GET /health system endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


def test_api_database_health(client):
    """Verifies GET /health/db active database probe."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["core_tables_healthy"] is True
    assert "latency_ms" in data


def test_api_admin_database_health_authenticated(client, auth_headers):
    """Verifies GET /admin/db-health requires authentication and returns diagnostics."""
    # Unauthenticated should fail
    unauth_resp = client.get("/admin/db-health")
    assert unauth_resp.status_code == 401

    # Authenticated should return diagnostic details
    auth_resp = client.get("/admin/db-health", headers=auth_headers)
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["status"] == "connected"
    assert data["core_tables_healthy"] is True
    assert data["dialect"] == "postgresql"
