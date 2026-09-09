"""
Audit Logger Service
--------------------
Centralized logging utility for recording immutable security, operational,
and user activity events across the platform.

Day 46 — Activity History Backend
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.audit_events import (
    AuditEventType,
    AUDIT_CATEGORIES,
    get_event_category,
    format_event_description,
)
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse

logger = logging.getLogger(__name__)


def extract_client_info(request: Optional[Request]) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely extracts client IP address and user-agent string from a FastAPI Request.
    Handles proxies (X-Forwarded-For) and enforces field lengths.
    """
    if not request:
        return None, None

    ip_address = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    elif request.client:
        ip_address = request.client.host

    user_agent = request.headers.get("user-agent")
    if user_agent and len(user_agent) > 255:
        user_agent = user_agent[:252] + "..."

    return ip_address, user_agent


def log_activity(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    status: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    commit: bool = True,
) -> Optional[AuditLog]:
    """
    Records an immutable audit trail entry in `audit_logs`.

    Guaranteed not to raise an unhandled exception so business workflows
    are never blocked by logging telemetry.
    """
    try:
        # Extract network details if request object provided
        if request:
            req_ip, req_ua = extract_client_info(request)
            ip_address = ip_address or req_ip
            user_agent = user_agent or req_ua

        # Truncate strings to match schema bounds safely
        safe_action = action[:100]
        safe_status = (status or "SUCCESS")[:20]
        safe_ip = ip_address[:45] if ip_address else None
        safe_ua = user_agent[:255] if user_agent else None

        entry = AuditLog(
            user_id=user_id,
            action=safe_action,
            resource_id=resource_id,
            status=safe_status,
            ip_address=safe_ip,
            user_agent=safe_ua,
            metadata_json=metadata,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        return entry
    except Exception as exc:
        logger.warning("Failed to record audit log for action %s: %s", action, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def get_user_activity(
    db: Session,
    user_id: int,
    category: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AuditLogResponse], int]:
    """
    Queries paginated activity timeline entries for a specific user with
    optional multi-criteria filtering. Enriches each item with plain-English
    descriptions and event categories.
    """
    query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

    # 1. Filter by category
    if category and category.upper() in AUDIT_CATEGORIES:
        allowed_actions = [e.value for e in AUDIT_CATEGORIES[category.upper()]]
        query = query.filter(AuditLog.action.in_(allowed_actions))

    # 2. Filter by specific action
    if action:
        query = query.filter(AuditLog.action == action)

    # 3. Filter by status
    if status:
        query = query.filter(AuditLog.status == status)

    # 4. Date range filters
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    total = query.count()

    # Sort most recent first
    records = (
        query.order_by(desc(AuditLog.timestamp))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for r in records:
        items.append(
            AuditLogResponse(
                id=r.id,
                user_id=r.user_id,
                action=r.action,
                resource_id=r.resource_id,
                status=r.status,
                ip_address=r.ip_address,
                user_agent=r.user_agent,
                metadata_json=r.metadata_json,
                timestamp=r.timestamp,
                category=get_event_category(r.action),
                description=format_event_description(r.action, r.metadata_json),
            )
        )

    return items, total
