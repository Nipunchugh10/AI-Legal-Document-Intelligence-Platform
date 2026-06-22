"""
Alembic Migration Environment
------------------------------
Configured to:
  1. Load DATABASE_URL from the project's .env (via app.core.config)
  2. Import all SQLAlchemy models so autogenerate detects the full schema
  3. Support both offline (SQL script) and online (live DB) migration modes

Day 3 — Database Design and Migrations
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure the `backend/` directory is on the Python path so that
# `app.*` imports resolve correctly when alembic is invoked from backend/
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Import settings first (loads .env), then import all models so Alembic
# autogenerate sees the full schema via Base.metadata
# ---------------------------------------------------------------------------
from app.core.config import get_settings          # noqa: E402
from app.core.database import Base               # noqa: E402
import app.models                                 # noqa: F401, E402  — registers all models on Base

settings = get_settings()

# Alembic Config object (wraps alembic.ini)
config = context.config

# Override sqlalchemy.url with the value from .env so we never need to
# hard-code a connection string inside alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to use for autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout without a live DB connection
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connect to the live DB and apply migrations
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
