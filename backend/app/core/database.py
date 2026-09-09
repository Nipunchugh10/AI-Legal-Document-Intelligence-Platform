"""
Database Module — Day 52: Cloud Database Setup & Resilience
------------------------------------------------------------
SQLAlchemy engine, session factory, Base class for ORM models,
connection URL normalization, and cloud database connectivity diagnostics.
"""

from __future__ import annotations

import time
import logging
from typing import Any
from sqlalchemy import create_engine, inspect, text, Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings, normalize_database_url, mask_database_url

logger = logging.getLogger(__name__)
settings = get_settings()

# Expected core application tables managed by Alembic migrations
CORE_TABLES: list[str] = [
    "analyses",
    "audit_logs",
    "contracts",
    "conversation_messages",
    "conversations",
    "email_otp_verifications",
    "user_sessions",
    "users",
]

# --- Normalized Database Connection String ---
# Converts postgres:// -> postgresql:// and enforces SSL for cloud endpoints
NORMALIZED_DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

# --- SQLAlchemy Engine ---
# Optimized connection pool configuration for cloud & serverless resilience (Neon, Supabase, Render)
# pool_pre_ping=True: prevents dropped socket errors when serverless connection proxies terminate idle connections
# pool_recycle=1800: proactively refreshes connections every 30 minutes
engine = create_engine(
    NORMALIZED_DATABASE_URL,
    pool_size=20,          # Persistent connection pool
    max_overflow=10,       # Extra burst connections during peak load
    pool_timeout=30,       # Timeout in seconds before raising pool exhaustion error
    pool_recycle=1800,     # Recycle connections every 30 minutes to prevent stale dropped sockets
    pool_pre_ping=True,    # Test connection liveness before checkout
    echo=settings.DEBUG,   # Log SQL statements in development
)

# --- Session Factory ---
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# --- Declarative Base ---
# All ORM models will inherit from this
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is properly closed after the request completes.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection(
    target_engine: Engine | None = None,
    target_url: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """
    Performs an active database connectivity probe and schema diagnostic.

    Args:
        target_engine: Optional existing SQLAlchemy Engine to test.
        target_url: Optional database connection URL string to probe (normalized automatically).
        timeout: Socket connection timeout in seconds.

    Returns:
        dict containing:
            - status: "connected" | "error"
            - database: name of database
            - host: host address
            - port: port number
            - dialect: database dialect (e.g. "postgresql", "sqlite")
            - version: database server version string
            - ssl_in_use: bool indicating whether connection is encrypted with SSL
            - latency_ms: roundtrip ping query latency in milliseconds
            - tables_count: number of existing tables discovered
            - tables: sorted list of existing table names
            - core_tables_healthy: bool indicating if all core application tables are present
            - missing_tables: list of missing core tables (if any)
            - alembic_version: current alembic migration revision (if alembic_version table exists)
            - error: error message string if failed (credentials strictly redacted)
    """
    temp_engine: Engine | None = None
    test_engine = target_engine

    if target_url is not None:
        norm_url = normalize_database_url(target_url)
        connect_args: dict[str, Any] = {}
        if norm_url.startswith("postgresql"):
            connect_args["connect_timeout"] = int(timeout)
        elif norm_url.startswith("sqlite"):
            connect_args["timeout"] = timeout

        temp_engine = create_engine(
            norm_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        test_engine = temp_engine
    elif test_engine is None:
        test_engine = engine

    # Extract connection coordinates safely
    db_name = getattr(test_engine.url, "database", None)
    db_host = getattr(test_engine.url, "host", None)
    db_port = getattr(test_engine.url, "port", None)
    dialect_name = getattr(test_engine.dialect, "name", "unknown")

    try:
        start_time = time.perf_counter()
        with test_engine.connect() as conn:
            # 1. Ping probe query
            conn.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 2. Server version
            version_str: str | None = None
            try:
                version_str = conn.execute(text("SELECT version()")).scalar()
            except Exception:
                try:
                    version_str = conn.execute(text("SELECT sqlite_version()")).scalar()
                except Exception:
                    version_str = "unknown"

            # 3. SSL verification (for PostgreSQL)
            ssl_active = False
            try:
                raw_conn = getattr(conn.connection, "dbapi_connection", None)
                if raw_conn is not None:
                    if hasattr(raw_conn, "info") and hasattr(raw_conn.info, "ssl_in_use"):
                        ssl_active = bool(raw_conn.info.ssl_in_use)
                    elif hasattr(raw_conn, "ssl_in_use"):
                        ssl_active = bool(raw_conn.ssl_in_use)
            except Exception:
                pass

            if not ssl_active and dialect_name == "postgresql":
                try:
                    # Built-in PostgreSQL system view for SSL connection status
                    res = conn.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")).scalar()
                    if res is not None:
                        ssl_active = bool(res)
                except Exception:
                    pass

            # 4. Tables and schema health
            insp = inspect(conn)
            existing_tables = sorted(insp.get_table_names())
            missing_tables = [tbl for tbl in CORE_TABLES if tbl not in existing_tables]

            # 5. Alembic migration revision
            alembic_rev: str | None = None
            if "alembic_version" in existing_tables:
                try:
                    alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                except Exception:
                    pass

            return {
                "status": "connected",
                "database": db_name,
                "host": db_host,
                "port": db_port,
                "dialect": conn.dialect.name,
                "version": version_str,
                "ssl_in_use": ssl_active,
                "latency_ms": latency_ms,
                "tables_count": len(existing_tables),
                "tables": existing_tables,
                "core_tables_healthy": len(missing_tables) == 0,
                "missing_tables": missing_tables,
                "alembic_version": alembic_rev,
                "error": None,
            }

    except Exception as e:
        error_msg = str(e)
        # Redact any password that may appear in error message or stack trace
        if test_engine and hasattr(test_engine, "url") and test_engine.url.password:
            error_msg = error_msg.replace(test_engine.url.password, "***REDACTED***")

        logger.error("Database connectivity diagnostic failed: %s", error_msg)
        return {
            "status": "error",
            "database": db_name,
            "host": db_host,
            "port": db_port,
            "dialect": dialect_name,
            "version": None,
            "ssl_in_use": False,
            "latency_ms": None,
            "tables_count": 0,
            "tables": [],
            "core_tables_healthy": False,
            "missing_tables": CORE_TABLES,
            "alembic_version": None,
            "error": error_msg,
        }
    finally:
        if temp_engine is not None:
            temp_engine.dispose()
