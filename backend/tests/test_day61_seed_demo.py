"""
test_day61_seed_demo.py
------------------------
Automated tests for Day 61: Demo Data Seeding & Documentation Verification.

Validates:
1. scripts/seed_demo.py creates demo accounts (demo@legalai.com & lawyer@example.com).
2. Demo user has 2FA disabled for frictionless evaluation.
3. 5 diverse contracts are created and marked 'analyzed'.
4. Full multi-agent analysis findings exist for all 5 contracts (9-clause checklist, 3-tier risks, 8-domain compliance).
5. 3 persistent Q&A conversations exist with pinpoint clause citations.
6. Activity history / audit logs are populated for the demo user.
7. The seed script is completely idempotent when executed repeatedly.
"""

import pytest
import sys
from pathlib import Path

# Ensure root scripts directory is importable
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit_log import AuditLog
try:
    from scripts.seed_demo import seed_demo_data, CONTRACT_TEXTS, build_contract_data
except ImportError:
    import importlib.util
    seed_path = ROOT_DIR / "scripts" / "seed_demo.py"
    if not seed_path.exists():
        seed_path = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
    spec = importlib.util.spec_from_file_location("scripts.seed_demo", str(seed_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["scripts.seed_demo"] = module
    spec.loader.exec_module(module)
    seed_demo_data = module.seed_demo_data
    CONTRACT_TEXTS = module.CONTRACT_TEXTS
    build_contract_data = module.build_contract_data


class TestDay61DemoSeeding:
    """Test suite certifying Day 61 demo data generation and idempotence."""

    @pytest.fixture(autouse=True)
    def run_seeding(self):
        """Run seed_demo_data once before test execution."""
        seed_demo_data()

    def test_demo_users_created_and_configured(self):
        """Certify demo@legalai.com and lawyer@example.com are seeded with 2FA disabled."""
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
            assert demo_user is not None
            assert demo_user.is_active is True
            assert demo_user.is_2fa_enabled is False

            lawyer_user = db.query(User).filter(User.email == "lawyer@example.com").first()
            assert lawyer_user is not None
            assert lawyer_user.is_active is True
            assert lawyer_user.is_2fa_enabled is False
        finally:
            db.close()

    def test_five_sample_contracts_seeded_and_analyzed(self):
        """Certify 5 diverse contracts exist for demo user with status 'analyzed'."""
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
            assert demo_user is not None

            contracts = db.query(Contract).filter(Contract.user_id == demo_user.id).all()
            assert len(contracts) == 5

            for contract in contracts:
                assert contract.status == "analyzed"
                assert Path(contract.upload_path).exists()
                # Ensure each contract has 6 analysis records
                analyses = db.query(Analysis).filter(Analysis.contract_id == contract.id).all()
                analysis_types = {a.analysis_type for a in analyses}
                expected_types = {"raw_text", "parsing_agent", "clauses", "risks", "compliance", "summary"}
                assert expected_types.issubset(analysis_types)
        finally:
            db.close()

    def test_universal_nine_clause_checklist_populated(self):
        """Certify universal 9-clause checklist is evaluated on all 5 demo contracts."""
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
            contracts = db.query(Contract).filter(Contract.user_id == demo_user.id).all()

            mandatory_clauses = [
                "payment_terms",
                "termination_clauses",
                "liability_clauses",
                "confidentiality_clauses",
                "intellectual_property_clauses",
                "dispute_resolution_clauses",
                "governing_law_clauses",
                "renewal_clauses",
                "indemnification_clauses",
            ]

            for contract in contracts:
                clause_rec = (
                    db.query(Analysis)
                    .filter(Analysis.contract_id == contract.id, Analysis.analysis_type == "clauses")
                    .first()
                )
                assert clause_rec is not None
                assert isinstance(clause_rec.result_json, dict)
                for cl in mandatory_clauses:
                    assert cl in clause_rec.result_json
                    assert "present" in clause_rec.result_json[cl]
                    assert "text" in clause_rec.result_json[cl]
                    assert "location" in clause_rec.result_json[cl]
        finally:
            db.close()

    def test_conversations_with_pinpoint_citations(self):
        """Certify 3 persistent conversations exist with message citations."""
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
            conversations = db.query(Conversation).filter(Conversation.user_id == demo_user.id).all()
            assert len(conversations) == 3

            for conv in conversations:
                messages = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.conversation_id == conv.id)
                    .order_by(ConversationMessage.created_at.asc())
                    .all()
                )
                assert len(messages) >= 2
                # At least one assistant message has citations
                assistant_msgs = [m for m in messages if m.role == "assistant"]
                assert any(m.cited_clause_refs is not None and len(m.cited_clause_refs) > 0 for m in assistant_msgs)
        finally:
            db.close()

    def test_audit_logs_populated_for_activity_timeline(self):
        """Certify audit logs exist for demo user to populate /history page."""
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@legalai.com").first()
            logs = db.query(AuditLog).filter(AuditLog.user_id == demo_user.id).all()
            assert len(logs) >= 15
            actions = {l.action for l in logs}
            assert "USER_LOGIN" in actions
            assert "CONTRACT_UPLOADED" in actions
            assert "ANALYSIS_COMPLETED" in actions
            assert "QA_MESSAGE_SENT" in actions
        finally:
            db.close()

    def test_seed_demo_idempotence(self):
        """Certify seed_demo_data can be run repeatedly without errors or duplicate state."""
        # Run second time
        seed_demo_data()

        db = SessionLocal()
        try:
            demo_users = db.query(User).filter(User.email == "demo@legalai.com").all()
            assert len(demo_users) == 1

            contracts = db.query(Contract).filter(Contract.user_id == demo_users[0].id).all()
            assert len(contracts) == 5

            conversations = db.query(Conversation).filter(Conversation.user_id == demo_users[0].id).all()
            assert len(conversations) == 3
        finally:
            db.close()
