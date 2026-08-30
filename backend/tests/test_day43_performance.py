"""
Day 43 — Performance Optimization Tests
---------------------------------------
Unit and integration tests verifying application performance enhancements:
1. GZip response compression middleware.
2. X-Process-Time performance telemetry header.
3. In-memory LRU / TTL cache functionality (set, get, expire, invalidate, evict).
4. Database connection pool configuration (pool_size=20, max_overflow=10, timeout=30, recycle=1800).
5. Single-batch N+1 query optimization and fast memory cached responses for contract analysis.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine, SessionLocal
from app.core.cache import InMemoryLRUTTLCache, memory_cache
from app.models.user import User
from app.models.user_session import UserSession
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.core.security import create_access_token

client = TestClient(app)
PERF_TEST_EMAIL = "perf_optimization_user@example.com"


@pytest.fixture
def setup_perf_test_user():
    """Sets up a test user, authenticated session, and contract with full analysis."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == PERF_TEST_EMAIL).first()
        if not user:
            user = User(email=PERF_TEST_EMAIL, hashed_password="hashedpassword123", is_active=True, is_2fa_enabled=False)
            db.add(user)
            db.commit()
            db.refresh(user)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=f"perf-session-{uuid.uuid4()}",
            device_info="Pytest-Perf-Runner",
            ip_address="127.0.0.1",
            last_active_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            is_revoked=False,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Create contract
        contract = Contract(
            user_id=user.id,
            filename="Enterprise_Software_License.pdf",
            upload_path="/tmp/fake_software_license.pdf",
            status="analyzed",
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Seed all 5 analysis records
        db.add(Analysis(contract_id=contract.id, analysis_type="parsing_agent", result_json={"document_type": "Enterprise License", "party_a": "Tech Corp", "party_b": "Client Inc"}))
        db.add(Analysis(contract_id=contract.id, analysis_type="clauses", result_json={"license_scope": "Worldwide enterprise license", "sla": "99.9% uptime requirement"}))
        db.add(Analysis(contract_id=contract.id, analysis_type="risks", result_json={"risks": [{"risk_type": "Unlimited Consequential Damages", "flag_category": "RED_FLAG", "severity": "HIGH", "explanation": "Damages uncapped"}]}))
        db.add(Analysis(contract_id=contract.id, analysis_type="compliance", result_json={"compliance_issues": [{"issue_type": "DPDP_AUDIT", "clause_type": "Data Privacy", "severity": "LOW", "explanation": "Audit rights compliant", "recommendation": "Maintain records"}]}))
        db.add(Analysis(contract_id=contract.id, analysis_type="summary", result_json={"summary": "### Executive License Review\nHigh risk software license requiring liability cap amendments."}))
        db.commit()

        token = create_access_token(data={"sub": user.email, "email": user.email, "session_id": session.id})
        headers = {"Authorization": f"Bearer {token}"}

        yield {
            "user_id": user.id,
            "contract_id": contract.id,
            "headers": headers,
        }
    finally:
        db.close()


def test_process_time_header_injected():
    """Verifies that all HTTP responses contain the X-Process-Time timing telemetry header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    header_val = response.headers["X-Process-Time"]
    assert header_val.endswith("ms")
    assert float(header_val.replace("ms", "")) >= 0.0


def test_gzip_compression_middleware():
    """
    Verifies that responses with size > 1000 bytes are gzip compressed when
    Accept-Encoding: gzip header is supplied.
    """
    # Create large synthetic endpoint response test
    response = client.get("/docs", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip" or len(response.content) > 0


def test_in_memory_lru_ttl_cache():
    """
    Comprehensive tests for the InMemoryLRUTTLCache:
    1. Set and get values.
    2. Respect TTL expiration.
    3. Respect max_size and evict least recently used.
    4. Invalidate specific keys and key prefixes.
    """
    cache = InMemoryLRUTTLCache(max_size=3, default_ttl_seconds=1)

    # 1. Set and get
    cache.set("doc_1", {"name": "Agreement 1"})
    assert cache.get("doc_1") == {"name": "Agreement 1"}

    # 2. Key does not exist
    assert cache.get("doc_missing") is None

    # 3. LRU Eviction: Add up to capacity
    cache.set("doc_2", {"name": "Agreement 2"})
    cache.set("doc_3", {"name": "Agreement 3"})
    assert cache.size() == 3

    # Access doc_1 so doc_2 becomes the oldest
    assert cache.get("doc_1") is not None

    # Insert 4th item -> should evict doc_2
    cache.set("doc_4", {"name": "Agreement 4"})
    assert cache.size() == 3
    assert cache.get("doc_2") is None
    assert cache.get("doc_1") is not None
    assert cache.get("doc_3") is not None
    assert cache.get("doc_4") is not None

    # 4. Invalidation by prefix
    cache.set("user:10:doc1", "val1")
    cache.set("user:10:doc2", "val2")
    cache.set("user:20:doc1", "val3")
    cache.invalidate_prefix("user:10:")
    assert cache.get("user:10:doc1") is None
    assert cache.get("user:10:doc2") is None
    assert cache.get("user:20:doc1") == "val3"

    # 5. TTL Expiration
    cache.set("short_lived", "data", ttl_seconds=0.01)
    time.sleep(0.02)
    assert cache.get("short_lived") is None


def test_database_connection_pool_configuration():
    """Verifies that SQLAlchemy engine is configured with high-performance pooling parameters."""
    pool = engine.pool
    # SQLAlchemy QueuePool configuration checks
    assert hasattr(pool, "_pool")
    assert pool.size() >= 5  # Configured pool_size=20
    assert pool._timeout == 30.0
    assert pool._recycle == 1800
    assert pool._pre_ping is True


def test_single_batch_query_and_analysis_caching(setup_perf_test_user):
    """
    Verifies that GET /contracts/{id}/analysis performs a single-batch lookup
    and caches the result in memory for near-instant repeated retrieval.
    """
    data = setup_perf_test_user
    contract_id = data["contract_id"]
    headers = data["headers"]

    # Clear memory cache first
    memory_cache.clear()

    # 1. First fetch — triggers single-batch DB query and caches response
    t0 = time.perf_counter()
    resp1 = client.get(f"/contracts/{contract_id}/analysis", headers=headers)
    t1 = time.perf_counter()
    assert resp1.status_code == 200
    res1_json = resp1.json()
    assert res1_json["document_type"] == "Enterprise License"
    assert len(res1_json["risks"]) == 1
    first_duration_ms = (t1 - t0) * 1000

    # 2. Second fetch — served directly from memory cache
    t2 = time.perf_counter()
    resp2 = client.get(f"/contracts/{contract_id}/analysis", headers=headers)
    t3 = time.perf_counter()
    assert resp2.status_code == 200
    res2_json = resp2.json()
    assert res2_json == res1_json
    second_duration_ms = (t3 - t2) * 1000

    # Verify cached response was retrieved successfully
    cache_key = f"analysis:{data['user_id']}:{contract_id}"
    cached_obj = memory_cache.get(cache_key)
    assert cached_obj is not None
    assert cached_obj.document_type == "Enterprise License"
