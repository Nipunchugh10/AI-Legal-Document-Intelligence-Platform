"""
Admin & Operational Telemetry Router
------------------------------------
Provides administrative endpoints for AI quota usage telemetry, rate limit tracking,
and platform operational health.

Day 44 — Free AI Stack Resilience and Rate Limit Monitoring
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ai_usage_monitor import ai_usage_monitor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/ai-usage",
    status_code=status.HTTP_200_OK,
    summary="Get 24-Hour Gemini AI Quota Usage & Rate Limit Telemetry",
    description=(
        "Returns estimated 24-hour rolling request counts, daily quota percentages, "
        "warning threshold statuses, and multi-model cascade health for Google Gemini Free Tier."
    ),
)
async def get_ai_usage_telemetry(
    current_user: User = Depends(get_current_user),
):
    """
    Returns rolling 24-hour AI request metrics and quota consumption percentages.
    Protected endpoint accessible by authenticated users/administrators.
    """
    logger.info("Admin AI usage telemetry requested by user_id=%s", current_user.id)
    return ai_usage_monitor.get_usage_metrics()


@router.get(
    "/db-health",
    status_code=status.HTTP_200_OK,
    summary="Get Cloud Database Connectivity and Schema Diagnostics",
    description="Returns live database connection latency, version, SSL status, and table health.",
)
async def get_db_health(
    current_user: User = Depends(get_current_user),
):
    """
    Returns live cloud database diagnostic health check.
    Protected endpoint accessible by authenticated users/administrators.
    """
    from app.core.database import check_database_connection
    logger.info("Admin DB health check requested by user_id=%s", current_user.id)
    return check_database_connection()

