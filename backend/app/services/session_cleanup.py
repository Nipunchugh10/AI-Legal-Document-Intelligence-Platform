"""
Session Cleanup Service
-----------------------
Utility functions for cleaning up expired or idle user sessions.

Day 10 — Auto-Logout on Inactivity (Backend Support)
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.user_session import UserSession
from app.core.config import get_settings


def clean_expired_sessions(db: Session) -> int:
    """
    Query the database and mark expired or idle sessions as revoked.
    A session is considered expired if:
    1. It has exceeded the absolute session limit (expires_at < now) OR
    2. It has been idle longer than the allowed idle timeout (last_active_at < now - idle_timeout).

    Args:
        db: SQLAlchemy database session.

    Returns:
        The number of sessions revoked.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    idle_limit = timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)

    expired_sessions = (
        db.query(UserSession)
        .filter(
            (UserSession.is_revoked == False)
            & (
                (UserSession.expires_at < now)
                | (UserSession.last_active_at < now - idle_limit)
            )
        )
        .all()
    )

    for session in expired_sessions:
        session.is_revoked = True

    if expired_sessions:
        db.commit()

    return len(expired_sessions)
