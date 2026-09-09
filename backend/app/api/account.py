"""
Account & Privacy Router
------------------------
Endpoints for full account data portability, user-configurable activity log
retention policies, and verified multi-factor account deletion.

Day 48 — History Privacy, Retention, and Data Export
"""

from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.account import (
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    AccountDeleteOTPResponse,
    AccountDeleteRequest,
    AccountDeleteResponse,
)
from app.services import account_service

router = APIRouter(prefix="/account", tags=["Account & Privacy"])


@router.get(
    "/export",
    summary="Export all account data",
    description=(
        "Generates a complete, structured JSON archive containing all user contracts, "
        "multi-agent analysis results, interactive Q&A conversations, and activity audit logs."
    ),
)
def export_account_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates and streams a downloadable complete JSON compliance export."""
    payload = account_service.generate_account_export(db, current_user)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"legal_intel_export_user_{current_user.id}_{timestamp_str}.json"

    # Return as JSON with attachment disposition so browser triggers file download
    json_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/retention",
    response_model=RetentionPolicyResponse,
    summary="Get activity data retention policy",
    description="Retrieves the current user's activity audit log retention period in days.",
)
def get_retention_policy(
    current_user: User = Depends(get_current_user),
):
    """Returns the current data retention policy."""
    days = current_user.data_retention_days
    msg = (
        f"Activity logs are automatically purged after {days} days."
        if days is not None
        else "Activity logs are retained indefinitely."
    )
    return RetentionPolicyResponse(data_retention_days=days, message=msg)


@router.patch(
    "/retention",
    response_model=RetentionPolicyResponse,
    summary="Update activity data retention policy",
    description=(
        "Updates the activity log retention window (30, 90, 180, 365 days, or null for forever). "
        "Retroactively purges any records exceeding the newly specified duration."
    ),
)
def update_retention_policy(
    body: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configures activity log retention duration and executes immediate threshold cleanup."""
    retention_days, purged_count = account_service.update_retention_policy(
        db, current_user, body.data_retention_days
    )

    if retention_days is not None:
        msg = f"Retention policy updated to {retention_days} days. {purged_count} expired records were purged."
    else:
        msg = "Retention policy updated to indefinite (logs will not expire)."

    return RetentionPolicyResponse(data_retention_days=retention_days, message=msg)


@router.post(
    "/delete-otp",
    response_model=AccountDeleteOTPResponse,
    summary="Request OTP code for account deletion",
    description="Dispatches a 6-digit confirmation code to the user's email to verify account deletion intent.",
)
def request_deletion_otp(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sends a fresh OTP confirmation code for account deletion."""
    account_service.request_account_deletion_otp(db, current_user)
    return AccountDeleteOTPResponse(
        message="Deletion confirmation code dispatched to your registered email address."
    )


@router.delete(
    "",
    response_model=AccountDeleteResponse,
    summary="Permanently delete account and all data",
    description=(
        "Permanently deletes user account, contract documents, ChromaDB vector embeddings, "
        "and Q&A conversations. Requires current password and fresh Email OTP confirmation."
    ),
)
def delete_account(
    body: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently purges account and all child entities after strict password + OTP validation."""
    contracts_count, convos_count = account_service.delete_account_cascade(
        db=db,
        user=current_user,
        password=body.password,
        otp_code=body.otp_code,
    )

    return AccountDeleteResponse(
        message="Your account and all associated contracts, analyses, and conversations have been permanently deleted.",
        deleted_contracts_count=contracts_count,
        deleted_conversations_count=convos_count,
    )
