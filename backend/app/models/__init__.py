"""
Models Package
--------------
Import all ORM models here so that Alembic's autogenerate can discover
the full schema when it inspects `Base.metadata`.

Current models:
  User                  → users table
  Contract              → contracts table
  Analysis              → analyses table
  AuditLog              → audit_logs table
  UserSession           → user_sessions table
  PhoneOTPVerification  → phone_otp_verifications table
"""

from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.audit_log import AuditLog
from app.models.user_session import UserSession
from app.models.email_otp import EmailOTPVerification

__all__ = [
    "User",
    "Contract",
    "Analysis",
    "AuditLog",
    "UserSession",
    "EmailOTPVerification",
]
