"""
Audit Event Taxonomy
--------------------
Standardized event type definitions and taxonomy categories for the
AI Legal Document Intelligence Platform's security audit trail and
activity history subsystems.

Day 45 — History and Conversation Data Architecture
"""

from enum import Enum
from typing import Any, Dict, Optional


class AuditEventType(str, Enum):
    """
    Formalized audit event constants across 5 operational domains:
    1. Authentication & Session Security
    2. Contract Lifecycle & Ingestion
    3. Intelligence & Multi-Agent Analysis
    4. Interactive Q&A & Search
    5. Account Governance & Privacy
    """

    # 1. Authentication & Session Security
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    TWO_FACTOR_OTP_REQUESTED = "TWO_FACTOR_OTP_REQUESTED"
    TWO_FACTOR_LOGIN_VERIFIED = "TWO_FACTOR_LOGIN_VERIFIED"
    TWO_FACTOR_VERIFICATION_FAILED = "TWO_FACTOR_VERIFICATION_FAILED"
    TWO_FACTOR_ENABLED = "TWO_FACTOR_ENABLED"
    TWO_FACTOR_DISABLED = "TWO_FACTOR_DISABLED"

    # 2. Contract Lifecycle & Ingestion
    CONTRACT_UPLOADED = "CONTRACT_UPLOADED"
    CONTRACT_PROCESSED = "CONTRACT_PROCESSED"
    CONTRACT_VIEWED = "CONTRACT_VIEWED"
    CONTRACT_DELETED = "CONTRACT_DELETED"

    # 3. Intelligence & Multi-Agent Analysis
    ANALYSIS_QUEUED = "ANALYSIS_QUEUED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    CONTRACT_ANALYZED = "CONTRACT_ANALYZED"

    # 4. Interactive Q&A & Search
    QA_CONVERSATION_CREATED = "QA_CONVERSATION_CREATED"
    QA_MESSAGE_SENT = "QA_MESSAGE_SENT"
    COMPARISON_RUN = "COMPARISON_RUN"
    SEARCH_PERFORMED = "SEARCH_PERFORMED"

    # 5. Account Governance & Privacy
    DATA_EXPORTED = "DATA_EXPORTED"
    DATA_RETENTION_UPDATED = "DATA_RETENTION_UPDATED"
    ACCOUNT_DELETE_OTP_REQUESTED = "ACCOUNT_DELETE_OTP_REQUESTED"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"


# Category Groups for Frontend Filtering
AUDIT_CATEGORIES = {
    "AUTH": {
        AuditEventType.USER_REGISTERED,
        AuditEventType.USER_LOGIN,
        AuditEventType.USER_LOGIN_FAILED,
        AuditEventType.USER_LOGOUT,
        AuditEventType.SESSION_EXPIRED,
        AuditEventType.TWO_FACTOR_OTP_REQUESTED,
        AuditEventType.TWO_FACTOR_LOGIN_VERIFIED,
        AuditEventType.TWO_FACTOR_VERIFICATION_FAILED,
        AuditEventType.TWO_FACTOR_ENABLED,
        AuditEventType.TWO_FACTOR_DISABLED,
    },
    "CONTRACTS": {
        AuditEventType.CONTRACT_UPLOADED,
        AuditEventType.CONTRACT_PROCESSED,
        AuditEventType.CONTRACT_VIEWED,
        AuditEventType.CONTRACT_DELETED,
    },
    "ANALYSIS": {
        AuditEventType.ANALYSIS_QUEUED,
        AuditEventType.ANALYSIS_STARTED,
        AuditEventType.ANALYSIS_COMPLETED,
        AuditEventType.ANALYSIS_FAILED,
        AuditEventType.CONTRACT_ANALYZED,
    },
    "CHAT": {
        AuditEventType.QA_CONVERSATION_CREATED,
        AuditEventType.QA_MESSAGE_SENT,
    },
    "SEARCH": {
        AuditEventType.SEARCH_PERFORMED,
        AuditEventType.COMPARISON_RUN,
    },
    "SECURITY": {
        AuditEventType.DATA_EXPORTED,
        AuditEventType.DATA_RETENTION_UPDATED,
        AuditEventType.ACCOUNT_DELETE_OTP_REQUESTED,
        AuditEventType.ACCOUNT_DELETED,
    },
}

# Reverse lookup for rapid category classification
EVENT_TO_CATEGORY: Dict[str, str] = {
    event.value: category
    for category, events in AUDIT_CATEGORIES.items()
    for event in events
}

# Human-readable templates for plain-English activity timeline presentation
EVENT_HUMAN_DESCRIPTIONS: Dict[str, str] = {
    AuditEventType.USER_REGISTERED.value: "Created a new account",
    AuditEventType.USER_LOGIN.value: "Logged in successfully",
    AuditEventType.USER_LOGIN_FAILED.value: "Failed login attempt",
    AuditEventType.USER_LOGOUT.value: "Logged out",
    AuditEventType.SESSION_EXPIRED.value: "Session expired due to inactivity",
    AuditEventType.TWO_FACTOR_OTP_REQUESTED.value: "Requested 2FA verification code",
    AuditEventType.TWO_FACTOR_LOGIN_VERIFIED.value: "Completed 2FA verification",
    AuditEventType.TWO_FACTOR_VERIFICATION_FAILED.value: "Invalid 2FA code entered",
    AuditEventType.TWO_FACTOR_ENABLED.value: "Enabled Two-Factor Authentication",
    AuditEventType.TWO_FACTOR_DISABLED.value: "Disabled Two-Factor Authentication",
    AuditEventType.CONTRACT_UPLOADED.value: "Uploaded document: {filename}",
    AuditEventType.CONTRACT_PROCESSED.value: "Extracted text and indexed {filename}",
    AuditEventType.CONTRACT_VIEWED.value: "Viewed contract {filename}",
    AuditEventType.CONTRACT_DELETED.value: "Deleted contract {filename}",
    AuditEventType.ANALYSIS_QUEUED.value: "Queued background analysis for {filename}",
    AuditEventType.ANALYSIS_STARTED.value: "Started multi-agent analysis for {filename}",
    AuditEventType.ANALYSIS_COMPLETED.value: "Completed multi-agent legal analysis for {filename}",
    AuditEventType.ANALYSIS_FAILED.value: "Analysis failed for {filename}",
    AuditEventType.CONTRACT_ANALYZED.value: "Analyzed contract {filename}",
    AuditEventType.QA_CONVERSATION_CREATED.value: "Started new conversation for {filename}",
    AuditEventType.QA_MESSAGE_SENT.value: "Asked question about {filename}",
    AuditEventType.COMPARISON_RUN.value: "Compared contract versions",
    AuditEventType.SEARCH_PERFORMED.value: "Searched contract portfolio for '{query}'",
    AuditEventType.DATA_EXPORTED.value: "Exported personal account data archive",
    AuditEventType.DATA_RETENTION_UPDATED.value: "Updated activity retention policy",
    AuditEventType.ACCOUNT_DELETE_OTP_REQUESTED.value: "Requested account deletion confirmation code",
    AuditEventType.ACCOUNT_DELETED.value: "Permanently deleted account and all associated data",
}


def get_event_category(action: str) -> str:
    """Returns the high-level category for a given audit event action."""
    return EVENT_TO_CATEGORY.get(action, "GENERAL")


def format_event_description(action: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Renders a human-readable English description for an event, safely
    interpolating metadata fields (e.g. filename, query).
    """
    template = EVENT_HUMAN_DESCRIPTIONS.get(action, action.replace("_", " ").title())
    meta = metadata or {}
    try:
        # Provide fallback defaults so format string never crashes if key is absent
        safe_kwargs = {
            "filename": meta.get("filename") or meta.get("contract_name") or "document",
            "query": meta.get("query") or meta.get("q") or "contracts",
        }
        return template.format(**safe_kwargs)
    except Exception:
        return template
