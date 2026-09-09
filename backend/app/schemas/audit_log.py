"""
Audit Log Schemas
-----------------
Pydantic v2 validation models for recording and querying the immutable
security and activity audit trail.

Day 45 — History and Conversation Data Architecture
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    """Base audit log properties."""

    action: str = Field(..., max_length=100, description="Standardized event action identifier")
    resource_id: Optional[int] = Field(None, description="Primary affected entity ID")
    status: str = Field("SUCCESS", max_length=20, description="Execution status: SUCCESS, FAILURE, WARNING")
    ip_address: Optional[str] = Field(None, max_length=45, description="Client IP address")
    user_agent: Optional[str] = Field(None, max_length=255, description="Client browser / device user agent")
    metadata_json: Optional[Dict[str, Any]] = Field(
        None, description="Arbitrary context bag (filename, query, duration_ms, error details)"
    )


class AuditLogCreate(AuditLogBase):
    """Schema for recording a new audit log event."""

    user_id: Optional[int] = Field(None, description="Initiating user ID if authenticated")


class AuditLogResponse(AuditLogBase):
    """Schema for returning audit trail entries to clients."""

    id: int
    user_id: Optional[int]
    timestamp: datetime
    category: Optional[str] = Field(None, description="High-level grouping: AUTH, CONTRACTS, ANALYSIS, etc.")
    description: Optional[str] = Field(None, description="Human-readable plain English narrative")

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilterParams(BaseModel):
    """Query parameter validation for filtering user activity history."""

    category: Optional[str] = Field(None, description="Filter by event category (AUTH, CONTRACTS, etc.)")
    action: Optional[str] = Field(None, description="Filter by specific AuditEventType")
    status: Optional[str] = Field(None, description="Filter by status (SUCCESS, FAILURE)")
    start_date: Optional[datetime] = Field(None, description="Filter events after this timestamp")
    end_date: Optional[datetime] = Field(None, description="Filter events before this timestamp")
    limit: int = Field(50, ge=1, le=200, description="Pagination page size")
    offset: int = Field(0, ge=0, description="Pagination offset")


class AuditLogFeedResponse(BaseModel):
    """Paginated response wrapper for activity logs."""

    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
