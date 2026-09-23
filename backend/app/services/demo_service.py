"""
Demo Data Service
-----------------
Ensures demo user accounts and evaluation datasets are provisioned and synchronized
across cloud databases, Hugging Face Spaces, and local environments.
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)

DEMO_ACCOUNTS = {
    "demo@legalai.com": "DemoPassword2026!",
    "lawyer@example.com": "SecurePassword123!",
}


def _invoke_seed_demo_data() -> bool:
    """Dynamically locates and executes seed_demo_data()."""
    # Try direct imports
    try:
        from scripts.seed_demo import seed_demo_data
        seed_demo_data()
        return True
    except Exception:
        pass

    try:
        from backend.scripts.seed_demo import seed_demo_data
        seed_demo_data()
        return True
    except Exception:
        pass

    # Fallback to direct file loading
    try:
        import importlib.util
        here = Path(__file__).resolve()
        candidates = [
            here.parents[2] / "scripts" / "seed_demo.py",
            here.parents[1] / "scripts" / "seed_demo.py",
            Path.cwd() / "scripts" / "seed_demo.py",
            Path.cwd() / "backend" / "scripts" / "seed_demo.py",
        ]
        for p in candidates:
            if p.exists():
                spec = importlib.util.spec_from_file_location("seed_demo_module", str(p))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "seed_demo_data"):
                        mod.seed_demo_data()
                        return True
    except Exception as e:
        logger.error("Failed to load and execute seed_demo_data: %s", e)
    return False


def ensure_demo_accounts_synced(db: Optional[Session] = None) -> bool:
    """
    Guarantees demo accounts (demo@legalai.com & lawyer@example.com) exist,
    are active, have 2FA disabled, and match their canonical passwords.
    """
    close_db = False
    if db is None:
        try:
            db = SessionLocal()
            close_db = True
        except Exception as e:
            logger.debug("Database not available for demo check: %s", e)
            return False

    try:
        demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
        if not demo_user:
            logger.info("Demo user demo@legalai.com not found. Seeding evaluation data...")
            seeded = _invoke_seed_demo_data()
            if seeded:
                logger.info("Demo evaluation dataset seeded successfully.")
                return True
            return False

        # Demo user exists; ensure credentials and active flags match canonical demo settings
        for email, pwd in DEMO_ACCOUNTS.items():
            user = db.query(User).filter(User.email == email).first()
            if user:
                needs_update = False
                if not verify_password(pwd, user.hashed_password):
                    user.hashed_password = hash_password(pwd)
                    needs_update = True
                if not user.is_active:
                    user.is_active = True
                    needs_update = True
                if user.is_2fa_enabled:
                    user.is_2fa_enabled = False
                    needs_update = True
                if needs_update:
                    db.commit()
                    db.refresh(user)
                    logger.info("Repaired credentials for %s", email)
            else:
                # One of the accounts was missing; run seed
                _invoke_seed_demo_data()
                break

        return True
    except Exception as e:
        logger.warning("Error checking or syncing demo accounts: %s", e)
        return False
    finally:
        if close_db and db:
            db.close()
