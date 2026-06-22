"""
Models Package
--------------
Import all ORM models here so that Alembic's autogenerate can discover
the full schema when it inspects `Base.metadata`.

Current models (Day 3):
  User        → users table
  Contract    → contracts table
  Analysis    → analyses table
  AuditLog    → audit_logs table

Future models — stubs for upcoming phases:
  UserSession            → user_sessions table          (Phase 2A, Day 11)
  PhoneOTPVerification   → phone_otp_verifications table (Phase 2A, Day 12–13)
  Conversation           → conversations table           (Phase 6,  Day 46)
  ConversationMessage    → conversation_messages table   (Phase 6,  Day 46)
"""

from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Contract",
    "Analysis",
    "AuditLog",
]
