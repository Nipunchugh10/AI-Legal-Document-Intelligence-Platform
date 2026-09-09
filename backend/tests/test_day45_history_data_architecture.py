"""
Day 45 Test Suite — History and Conversation Data Architecture
--------------------------------------------------------------
Verifies the relational models, event taxonomy, cascading behavior,
and Pydantic validation for the activity audit trail and persistent
conversations subsystems.

Day 45 — History and Conversation Data Architecture
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.audit_events import (
    AuditEventType,
    get_event_category,
    format_event_description,
    AUDIT_CATEGORIES,
)
from app.models.user import User
from app.models.contract import Contract
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, ConversationMessage
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationMessageCreate,
    ConversationMessageResponse,
)
from app.schemas.audit_log import (
    AuditLogResponse,
    AuditLogFilterParams,
    AuditLogFeedResponse,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session for fast, isolated testing of ORM relations."""
    # SQLite with foreign key enforcement
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Enable foreign keys in SQLite
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_audit_event_taxonomy_integrity():
    """Verify all event types belong to taxonomy categories and format properly."""
    # 1. Verify key events exist in enum
    assert AuditEventType.USER_LOGIN.value == "USER_LOGIN"
    assert AuditEventType.CONTRACT_UPLOADED.value == "CONTRACT_UPLOADED"
    assert AuditEventType.ANALYSIS_QUEUED.value == "ANALYSIS_QUEUED"
    assert AuditEventType.QA_MESSAGE_SENT.value == "QA_MESSAGE_SENT"
    assert AuditEventType.COMPARISON_RUN.value == "COMPARISON_RUN"
    assert AuditEventType.SEARCH_PERFORMED.value == "SEARCH_PERFORMED"
    assert AuditEventType.DATA_EXPORTED.value == "DATA_EXPORTED"

    # 2. Check category mappings
    assert get_event_category(AuditEventType.USER_LOGIN.value) == "AUTH"
    assert get_event_category(AuditEventType.CONTRACT_UPLOADED.value) == "CONTRACTS"
    assert get_event_category(AuditEventType.ANALYSIS_COMPLETED.value) == "ANALYSIS"
    assert get_event_category(AuditEventType.QA_MESSAGE_SENT.value) == "CHAT"
    assert get_event_category(AuditEventType.SEARCH_PERFORMED.value) == "SEARCH"
    assert get_event_category(AuditEventType.DATA_EXPORTED.value) == "SECURITY"
    assert get_event_category("UNKNOWN_ACTION") == "GENERAL"

    # 3. Check plain-English formatters
    desc_login = format_event_description(AuditEventType.USER_LOGIN.value)
    assert "Logged in successfully" in desc_login

    desc_upload = format_event_description(
        AuditEventType.CONTRACT_UPLOADED.value, {"filename": "Employment_NDA.pdf"}
    )
    assert "Uploaded document: Employment_NDA.pdf" in desc_upload

    desc_search = format_event_description(
        AuditEventType.SEARCH_PERFORMED.value, {"query": "indemnity clause"}
    )
    assert "Searched contract portfolio for 'indemnity clause'" in desc_search


def test_extended_audit_log_model_and_persistence(db_session):
    """Verify extended AuditLog fields (status, ip_address, user_agent, metadata_json)."""
    user = User(
        email="auditor@legalai.com",
        hashed_password="hashed_pass_123",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    audit_entry = AuditLog(
        user_id=user.id,
        action=AuditEventType.CONTRACT_UPLOADED.value,
        resource_id=101,
        status="SUCCESS",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 Chrome/120.0",
        metadata_json={"filename": "Master_Services.pdf", "size_bytes": 102400},
    )
    db_session.add(audit_entry)
    db_session.commit()
    db_session.refresh(audit_entry)

    assert audit_entry.id is not None
    assert audit_entry.status == "SUCCESS"
    assert audit_entry.ip_address == "192.168.1.100"
    assert audit_entry.user_agent == "Mozilla/5.0 Chrome/120.0"
    assert audit_entry.metadata_json["filename"] == "Master_Services.pdf"
    assert audit_entry.timestamp is not None


def test_conversation_and_messages_relational_structure(db_session):
    """Verify Conversation and ConversationMessage relationships and JSONB citations."""
    user = User(
        email="attorney@firm.com",
        hashed_password="hashed_pwd_456",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    contract = Contract(
        user_id=user.id,
        filename="Commercial_Lease.pdf",
        upload_path="/uploads/Commercial_Lease.pdf",
        status="analyzed",
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)

    # Create conversation
    convo = Conversation(
        user_id=user.id,
        contract_id=contract.id,
        title="Rent Escalation & Early Termination",
    )
    db_session.add(convo)
    db_session.commit()
    db_session.refresh(convo)

    # Add messages (turn 1: user question, turn 2: assistant response with citations)
    user_msg = ConversationMessage(
        conversation_id=convo.id,
        role="user",
        content="What is the rent escalation percentage per year?",
    )
    assistant_msg = ConversationMessage(
        conversation_id=convo.id,
        role="assistant",
        content="The rent escalates by 5% annually pursuant to Section 4.2.",
        cited_clause_refs=[
            {
                "clause_id": "clause-rent-4",
                "page": 3,
                "section": "4.2 Rent Adjustment",
                "text": "The monthly base rent shall increase by 5% on each anniversary...",
                "similarity": 0.92,
            }
        ],
    )
    db_session.add_all([user_msg, assistant_msg])
    db_session.commit()

    # Query back conversation
    retrieved_convo = db_session.query(Conversation).filter_by(id=convo.id).first()
    assert retrieved_convo is not None
    assert retrieved_convo.title == "Rent Escalation & Early Termination"
    assert len(retrieved_convo.messages) == 2
    assert retrieved_convo.messages[0].role == "user"
    assert retrieved_convo.messages[1].role == "assistant"
    assert len(retrieved_convo.messages[1].cited_clause_refs) == 1
    assert retrieved_convo.messages[1].cited_clause_refs[0]["similarity"] == 0.92

    # Verify back-populates relationships
    assert retrieved_convo.user.email == "attorney@firm.com"
    assert retrieved_convo.contract.filename == "Commercial_Lease.pdf"
    assert len(contract.conversations) == 1
    assert len(user.conversations) == 1


def test_cascade_deletion_on_contract(db_session):
    """Verify that deleting a contract cascade-deletes all associated conversations and messages."""
    user = User(email="client@corp.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.commit()

    contract = Contract(
        user_id=user.id,
        filename="Vendor_Agreement.pdf",
        upload_path="/uploads/Vendor.pdf",
        status="analyzed",
    )
    db_session.add(contract)
    db_session.commit()

    convo = Conversation(
        user_id=user.id,
        contract_id=contract.id,
        title="Vendor Warranty Discussion",
    )
    db_session.add(convo)
    db_session.commit()

    msg = ConversationMessage(
        conversation_id=convo.id,
        role="user",
        content="Is there an indemnification cap?",
    )
    db_session.add(msg)
    db_session.commit()

    convo_id = convo.id
    msg_id = msg.id

    # Delete contract
    db_session.delete(contract)
    db_session.commit()

    # Verify conversations and conversation_messages were cascaded
    assert db_session.query(Conversation).filter_by(id=convo_id).first() is None
    assert db_session.query(ConversationMessage).filter_by(id=msg_id).first() is None


def test_cascade_deletion_on_user(db_session):
    """Verify that deleting a user cascade-deletes conversations while preserving audit logs."""
    user = User(email="leaving_user@corp.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.commit()

    contract = Contract(
        user_id=user.id,
        filename="NDA.pdf",
        upload_path="/uploads/NDA.pdf",
        status="analyzed",
    )
    db_session.add(contract)
    db_session.commit()

    convo = Conversation(
        user_id=user.id,
        contract_id=contract.id,
        title="NDA Expiry",
    )
    db_session.add(convo)
    db_session.commit()

    msg = ConversationMessage(
        conversation_id=convo.id,
        role="user",
        content="When does the NDA expire?",
    )
    db_session.add(msg)

    audit_entry = AuditLog(
        user_id=user.id,
        action=AuditEventType.USER_LOGIN.value,
        status="SUCCESS",
    )
    db_session.add(audit_entry)
    db_session.commit()

    convo_id = convo.id
    audit_id = audit_entry.id

    # Delete user
    db_session.delete(user)
    db_session.commit()

    # Conversations should be cascade deleted
    assert db_session.query(Conversation).filter_by(id=convo_id).first() is None

    # AuditLog must NOT be deleted (compliance preservation), user_id becomes None
    surviving_audit = db_session.query(AuditLog).filter_by(id=audit_id).first()
    assert surviving_audit is not None
    assert surviving_audit.user_id is None
    assert surviving_audit.action == AuditEventType.USER_LOGIN.value


def test_pydantic_conversation_and_audit_schemas():
    """Verify Pydantic v2 serialization, validation, and JSONB handling."""
    # ConversationCreate validation
    create_req = ConversationCreate(contract_id=42, title="Test Thread")
    assert create_req.contract_id == 42
    assert create_req.title == "Test Thread"

    # Message serialization
    now = datetime.now(timezone.utc)
    msg_resp = ConversationMessageResponse(
        id=1,
        conversation_id=10,
        role="assistant",
        content="Here is the liability limit.",
        cited_clause_refs=[{"page": 2, "clause": "Limitation of Liability"}],
        created_at=now,
    )
    assert msg_resp.id == 1
    assert msg_resp.role == "assistant"
    assert msg_resp.cited_clause_refs[0]["page"] == 2

    # Detail response with messages
    detail_resp = ConversationDetailResponse(
        id=10,
        user_id=5,
        contract_id=42,
        title="Test Thread",
        created_at=now,
        last_message_at=now,
        message_count=1,
        contract_filename="NDA.pdf",
        messages=[msg_resp],
    )
    assert len(detail_resp.messages) == 1
    assert detail_resp.contract_filename == "NDA.pdf"

    # AuditLog schemas
    audit_resp = AuditLogResponse(
        id=99,
        user_id=5,
        action=AuditEventType.CONTRACT_ANALYZED.value,
        resource_id=42,
        status="SUCCESS",
        ip_address="127.0.0.1",
        timestamp=now,
        category="ANALYSIS",
        description="Analyzed contract NDA.pdf",
    )
    assert audit_resp.category == "ANALYSIS"
    assert audit_resp.status == "SUCCESS"

    filter_params = AuditLogFilterParams(category="AUTH", limit=25, offset=0)
    assert filter_params.limit == 25
    assert filter_params.category == "AUTH"

    feed_resp = AuditLogFeedResponse(
        items=[audit_resp],
        total=1,
        limit=25,
        offset=0,
    )
    assert feed_resp.total == 1
    assert len(feed_resp.items) == 1


def test_live_postgresql_schema_and_migration():
    """Verify live PostgreSQL container contains the migrated tables, indexes, and JSONB columns."""
    from app.core.database import SessionLocal, engine
    from sqlalchemy import text, inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify tables created
    assert "conversations" in tables
    assert "conversation_messages" in tables
    assert "audit_logs" in tables

    # Verify column structures in PostgreSQL
    convo_cols = {c["name"]: c for c in inspector.get_columns("conversations")}
    assert "title" in convo_cols
    assert "last_message_at" in convo_cols
    assert "user_id" in convo_cols
    assert "contract_id" in convo_cols

    msg_cols = {c["name"]: c for c in inspector.get_columns("conversation_messages")}
    assert "role" in msg_cols
    assert "content" in msg_cols
    assert "cited_clause_refs" in msg_cols

    audit_cols = {c["name"]: c for c in inspector.get_columns("audit_logs")}
    assert "status" in audit_cols
    assert "ip_address" in audit_cols
    assert "user_agent" in audit_cols

    # Verify indexes
    audit_indexes = {idx["name"] for idx in inspector.get_indexes("audit_logs")}
    assert "ix_audit_logs_user_id_timestamp" in audit_indexes
    assert "ix_audit_logs_action_timestamp" in audit_indexes

    convo_indexes = {idx["name"] for idx in inspector.get_indexes("conversations")}
    assert "ix_conversations_user_last_message" in convo_indexes
    assert "ix_conversations_contract_last_message" in convo_indexes

    # Test round-trip insert and delete in PostgreSQL
    db = SessionLocal()
    TEST_EMAIL = "day45_postgres_test@legalai.com"
    try:
        # Cleanup if old test run left anything
        existing_user = db.query(User).filter_by(email=TEST_EMAIL).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        user = User(email=TEST_EMAIL, hashed_password="pw", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

        contract = Contract(
            user_id=user.id,
            filename="Test_PG_Contract.pdf",
            upload_path="/uploads/test.pdf",
            status="analyzed",
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        convo = Conversation(
            user_id=user.id,
            contract_id=contract.id,
            title="Postgres JSONB Citation Test",
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

        msg = ConversationMessage(
            conversation_id=convo.id,
            role="assistant",
            content="Statutory indemnification clause analysis.",
            cited_clause_refs=[
                {"clause_id": "c1", "score": 0.95, "section": "Section 9"}
            ],
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Confirm JSONB round-trip in PostgreSQL
        retrieved_msg = db.query(ConversationMessage).filter_by(id=msg.id).first()
        assert retrieved_msg.cited_clause_refs[0]["score"] == 0.95

        # Confirm cascade deletion in PostgreSQL
        db.delete(user)
        db.commit()

        assert db.query(Conversation).filter_by(id=convo.id).first() is None
        assert db.query(ConversationMessage).filter_by(id=msg.id).first() is None
    finally:
        db.close()

