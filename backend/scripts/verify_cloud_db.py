#!/usr/bin/env python3
"""
Cloud Database Verification & Diagnostic CLI
--------------------------------------------
Validates PostgreSQL connectivity, SSL encryption, Alembic schema migration
status, and table health for cloud deployments (Hugging Face Spaces, Neon, Supabase, Render).

Usage:
    python backend/scripts/verify_cloud_db.py
    python backend/scripts/verify_cloud_db.py --url "postgres://..."
    python backend/scripts/verify_cloud_db.py --apply-migrations
    python backend/scripts/verify_cloud_db.py --json
"""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings, normalize_database_url, mask_database_url
from app.core.database import check_database_connection, CORE_TABLES


def get_alembic_heads(ini_path: str | Path | None = None) -> list[str]:
    """Retrieves target migration heads from Alembic version scripts."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    if ini_path is None:
        ini_path = _BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    script = ScriptDirectory.from_config(cfg)
    return script.get_heads()


def apply_migrations(db_url: str | None = None, ini_path: str | Path | None = None) -> bool:
    """Executes Alembic migrations to head programmatically."""
    from alembic.config import Config
    from alembic import command

    if ini_path is None:
        ini_path = _BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    if db_url:
        cfg.set_main_option("sqlalchemy.url", normalize_database_url(db_url))
    try:
        command.upgrade(cfg, "head")
        return True
    except Exception as e:
        print(f"[-] Migration execution failed: {e}", file=sys.stderr)
        return False


def run_verification(
    url: str | None = None,
    apply_migrate: bool = False,
    timeout: float = 10.0,
    json_output: bool = False,
) -> tuple[int, dict[str, Any]]:
    """
    Executes database verification probe and returns (exit_code, report_dict).
    """
    settings = get_settings()
    raw_url = url or settings.DATABASE_URL
    norm_url = normalize_database_url(raw_url)
    masked_target = mask_database_url(norm_url)

    # Initial diagnostic probe
    diag = check_database_connection(target_url=norm_url, timeout=timeout)
    diag["target_url_masked"] = masked_target

    # Determine alembic expected heads
    expected_heads: list[str] = []
    try:
        expected_heads = get_alembic_heads()
    except Exception as e:
        diag["alembic_heads_error"] = str(e)
    diag["expected_alembic_heads"] = expected_heads

    # Apply migrations if requested
    if apply_migrate and (not diag["core_tables_healthy"] or diag.get("alembic_version") not in expected_heads):
        migration_success = apply_migrations(db_url=norm_url)
        diag["migrations_applied"] = migration_success
        # Re-probe database state after migration
        diag = check_database_connection(target_url=norm_url, timeout=timeout)
        diag["target_url_masked"] = masked_target
        diag["expected_alembic_heads"] = expected_heads
        diag["migrations_applied"] = migration_success

    # Evaluation
    is_connected = diag["status"] == "connected"
    tables_healthy = diag.get("core_tables_healthy", False)
    exit_code = 0 if (is_connected and tables_healthy) else 1

    if json_output:
        print(json.dumps(diag, indent=2))
        return exit_code, diag

    # Human-readable formatted terminal output
    print("=" * 65)
    print(" Cloud Database Verification & Diagnostics (Day 52)")
    print("=" * 65)
    print(f" Target Endpoint   : {masked_target}")
    print(f" Dialect           : {diag.get('dialect', 'unknown')}")

    if not is_connected:
        print(f" Status            : [FAILED] Connection Error")
        print(f" Error Detail      : {diag.get('error')}")
        print("=" * 65)
        return 1, diag

    ssl_status_str = "Active (Encrypted / SSL)" if diag.get("ssl_in_use") else "Disabled (Unencrypted)"
    print(f" Status            : [PASS] Connected")
    print(f" Latency           : {diag.get('latency_ms')} ms")
    print(f" Server Version    : {diag.get('version', 'unknown')[:60]}...")
    print(f" SSL Security      : {ssl_status_str}")
    print(f" Discovered Tables : {diag.get('tables_count')} total")

    print("\n Schema & Core Tables Inspection:")
    all_present = True
    for tbl in CORE_TABLES:
        present = tbl in diag.get("tables", [])
        mark = "[OK]" if present else "[MISSING]"
        if not present:
            all_present = False
        print(f"   {mark:<10} {tbl}")

    print("\n Alembic Migration Status:")
    current_rev = diag.get("alembic_version")
    head_rev = expected_heads[0] if expected_heads else "unknown"
    rev_match = current_rev == head_rev and current_rev is not None
    match_str = "[OK] (Up-to-Date)" if rev_match else "[WARNING] (Out-of-Sync)"
    print(f"   Current Revision: {current_rev or 'None'} {match_str}")
    print(f"   Expected Head   : {head_rev}")

    print("=" * 65)
    if exit_code == 0:
        print(" Result: SUCCESS — Database is fully healthy and ready for deployment!")
    else:
        print(" Result: ACTION REQUIRED — Schema missing or migrations need applying.")
        print(" Hint: Run with --apply-migrations to instantiate the schema.")
    print("=" * 65)

    return exit_code, diag


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify cloud database connectivity, SSL status, and schema health.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="PostgreSQL connection string to test (defaults to DATABASE_URL in config).",
    )
    parser.add_argument(
        "--apply-migrations",
        action="store_true",
        help="Automatically apply Alembic migrations (upgrade head) if tables or revisions are missing.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Connection timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output diagnostics in JSON format.",
    )

    args = parser.parse_args()
    exit_code, _ = run_verification(
        url=args.url,
        apply_migrate=args.apply_migrations,
        timeout=args.timeout,
        json_output=args.json,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
