"""
Account & Privacy Service
-------------------------
Business logic for data export generation, user-configured activity log retention,
and secure multi-factor cascade account deletion.

Day 48 — History Privacy, Retention, and Data Export
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit_log import AuditLog
from app.models.email_otp import EmailOTPVerification
from app.models.user_session import UserSession
from app.core.security import verify_password
from app.core.audit_events import AuditEventType, format_event_description, get_event_category
from app.services.audit_logger import log_activity
from app.services.otp_service import send_otp, verify_otp
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)


def generate_account_export(db: Session, user: User) -> Dict[str, Any]:
    """
    Generates a structured, comprehensive, and portable JSON export
    of all data associated with the user account.
    """
    now = datetime.now(timezone.utc)

    # 1. User Profile Metadata
    account_profile = {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "is_2fa_enabled": user.is_2fa_enabled,
        "data_retention_days": user.data_retention_days,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    # 2. Contracts and Multi-Agent Analysis Results
    user_contracts = (
        db.query(Contract)
        .filter(Contract.user_id == user.id)
        .order_by(Contract.created_at.desc())
        .all()
    )

    contracts_data: List[Dict[str, Any]] = []
    for c in user_contracts:
        analyses = (
            db.query(Analysis)
            .filter(Analysis.contract_id == c.id)
            .order_by(Analysis.created_at.asc())
            .all()
        )
        contracts_data.append({
            "id": c.id,
            "filename": c.filename,
            "status": c.status,
            "upload_path": c.upload_path,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "analyses": [
                {
                    "id": a.id,
                    "analysis_type": a.analysis_type,
                    "result": a.result_json,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in analyses
            ],
        })

    # 3. Persistent Q&A Conversations & Messages
    user_conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.last_message_at.desc())
        .all()
    )

    conversations_data: List[Dict[str, Any]] = []
    for convo in user_conversations:
        messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == convo.id)
            .order_by(ConversationMessage.created_at.asc())
            .all()
        )
        conversations_data.append({
            "id": convo.id,
            "contract_id": convo.contract_id,
            "contract_filename": convo.contract.filename if convo.contract else None,
            "title": convo.title,
            "created_at": convo.created_at.isoformat() if convo.created_at else None,
            "last_message_at": convo.last_message_at.isoformat() if convo.last_message_at else None,
            "message_count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "cited_clause_refs": m.cited_clause_refs or [],
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        })

    # 4. Activity Audit Logs
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    activity_data: List[Dict[str, Any]] = [
        {
            "id": log.id,
            "action": log.action,
            "category": get_event_category(log.action),
            "description": format_event_description(log.action, log.metadata_json),
            "status": log.status,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "ip_address": log.ip_address,
            "metadata": log.metadata_json or {},
        }
        for log in logs
    ]

    export_payload: Dict[str, Any] = {
        "export_metadata": {
            "platform": "AI Legal Document Intelligence Platform",
            "export_version": "1.0",
            "exported_at": now.isoformat(),
            "user_id": user.id,
            "user_email": user.email,
        },
        "account_profile": account_profile,
        "contracts": contracts_data,
        "conversations": conversations_data,
        "activity_history": activity_data,
    }

    # Record data export in audit trail
    log_activity(
        db=db,
        action=AuditEventType.DATA_EXPORTED.value,
        user_id=user.id,
        status="SUCCESS",
        metadata={
            "contracts_count": len(contracts_data),
            "conversations_count": len(conversations_data),
            "activity_logs_count": len(activity_data),
        },
    )

    return export_payload


def get_retention_policy(user: User) -> Optional[int]:
    """Returns the active data retention period in days, or None for indefinite."""
    return user.data_retention_days


def apply_retention_cleanup(
    db: Session,
    user_id: Optional[int] = None,
    retention_days: Optional[int] = None,
) -> int:
    """
    Deletes audit log records older than the configured retention threshold.
    Returns the number of deleted records.
    """
    total_deleted = 0

    if user_id is not None:
        if retention_days is None:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.data_retention_days is None:
                return 0
            retention_days = user.data_retention_days

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user_id, AuditLog.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted

    # Global scheduled cleanup for all users with retention configured
    users_with_retention = db.query(User).filter(User.data_retention_days.isnot(None)).all()
    for u in users_with_retention:
        if u.data_retention_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=u.data_retention_days)
            deleted = (
                db.query(AuditLog)
                .filter(AuditLog.user_id == u.id, AuditLog.timestamp < cutoff)
                .delete(synchronize_session=False)
            )
            total_deleted += deleted

    if total_deleted > 0:
        db.commit()

    return total_deleted


def update_retention_policy(
    db: Session,
    user: User,
    retention_days: Optional[int],
) -> Tuple[Optional[int], int]:
    """
    Updates the user's data retention duration, applies retroactive cleanup if needed,
    and logs the event.
    """
    user.data_retention_days = retention_days
    db.commit()
    db.refresh(user)

    deleted_count = 0
    if retention_days is not None:
        deleted_count = apply_retention_cleanup(db, user_id=user.id, retention_days=retention_days)

    log_activity(
        db=db,
        action=AuditEventType.DATA_RETENTION_UPDATED.value,
        user_id=user.id,
        status="SUCCESS",
        metadata={
            "data_retention_days": retention_days,
            "purged_records": deleted_count,
        },
    )

    return (user.data_retention_days, deleted_count)


def request_account_deletion_otp(db: Session, user: User) -> None:
    """Dispatches a high-security OTP confirmation code to the user's email."""
    send_otp(db, user.email)

    log_activity(
        db=db,
        action=AuditEventType.ACCOUNT_DELETE_OTP_REQUESTED.value,
        user_id=user.id,
        status="SUCCESS",
        metadata={"email": user.email},
    )


def delete_account_cascade(
    db: Session,
    user: User,
    password: str,
    otp_code: str,
) -> Tuple[int, int]:
    """
    Performs permanent cascade account deletion after verifying password and fresh Email OTP.
    Cleans up:
    - Physical contract files from disk
    - ChromaDB vector embeddings
    - Email OTP verification records
    - User record (cascading to contracts, analyses, conversations, messages, sessions)
    - Preserves audit logs with user_id = NULL
    """
    # 1. Verify Password
    if not verify_password(password, user.hashed_password):
        log_activity(
            db=db,
            action=AuditEventType.ACCOUNT_DELETED.value,
            user_id=user.id,
            status="FAILURE",
            metadata={"reason": "Incorrect password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect account password.",
        )

    # 2. Verify OTP
    verify_otp(db, user.email, otp_code)

    # 3. Retrieve User Data Counts
    contracts = db.query(Contract).filter(Contract.user_id == user.id).all()
    contracts_count = len(contracts)
    conversations_count = db.query(Conversation).filter(Conversation.user_id == user.id).count()

    # 4. Clean up Physical Contract Files from Disk
    for c in contracts:
        if c.upload_path:
            file_path = Path(c.upload_path)
            if file_path.exists():
                try:
                    os.remove(file_path)
                    logger.info(f"[Account Deletion] Removed file: {file_path}")
                except Exception as e:
                    logger.warning(f"[Account Deletion] Error removing file {file_path}: {e}")

    # 5. Clean up ChromaDB Vector Embeddings
    try:
        vector_store = get_vector_store_service()
        for c in contracts:
            try:
                vector_store.delete_contract_chunks(c.id)
            except Exception as e:
                logger.warning(f"[Account Deletion] Error deleting ChromaDB chunks for contract {c.id}: {e}")
    except Exception as e:
        logger.warning(f"[Account Deletion] Could not access vector store during deletion: {e}")

    # 6. Record Permanent Deletion Audit Log
    # Note: user_id will become NULL upon commit due to ON DELETE SET NULL on audit_logs.user_id
    log_activity(
        db=db,
        action=AuditEventType.ACCOUNT_DELETED.value,
        user_id=user.id,
        status="SUCCESS",
        metadata={
            "deleted_user_email": user.email,
            "deleted_contracts_count": contracts_count,
            "deleted_conversations_count": conversations_count,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # 7. Clean up sessions and OTP verifications for this user
    db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    db.query(EmailOTPVerification).filter(EmailOTPVerification.email == user.email.strip().lower()).delete(synchronize_session=False)

    # 8. Delete User Record (Cascades to contracts, analyses, conversations, messages)
    db.delete(user)
    db.commit()

    logger.info(
        f"[Account Deletion] User {user.id} ({user.email}) permanently deleted with {contracts_count} contracts and {conversations_count} conversations."
    )

    return (contracts_count, conversations_count)
