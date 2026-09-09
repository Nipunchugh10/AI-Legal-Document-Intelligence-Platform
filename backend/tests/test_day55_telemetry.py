"""
Day 55 Test Suite — OpenTelemetry & Production Monitoring
---------------------------------------------------------
Certifies:
1. OpenTelemetry TracerProvider and MeterProvider initialization and resource attributes.
2. FastAPIInstrumentor and SQLAlchemyInstrumentor auto-instrumentation hooks.
3. Real-time API request throughput and latency percentile calculation (p50, p95, p99).
4. Database query duration telemetry hooks and slow query tracking.
5. Multi-agent contract analysis execution duration recording.
6. Authentication anomaly telemetry (failed logins, invalid OTPs, rate-limit hits, threat level).
7. GET /metrics endpoint in standard Prometheus exposition format.
8. GET /metrics?format=json structured JSON telemetry snapshot.
9. GET /admin/telemetry protected administrative endpoint.
10. GET /health telemetry status linkage.
11. Thread safety and concurrency during metric updates.
12. Test isolation and state reset capabilities.
"""

import threading
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.core.telemetry import (
    OPENTELEMETRY_AVAILABLE,
    metrics_collector,
    telemetry_manager,
    setup_telemetry,
)
from app.core.database import engine, SessionLocal
from app.models.user import User
from app.core.security import hash_password, create_access_token


@pytest.fixture(autouse=True)
def clean_telemetry_state():
    """Ensures each test starts with a clean telemetry slate."""
    metrics_collector.reset()
    yield
    metrics_collector.reset()


@pytest.fixture
def client():
    """Provides a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Creates a temporary test user and session, returning bearer authorization headers."""
    from app.core.security import create_refresh_token

    db = SessionLocal()
    email = "telemetry_tester@legalintel.ai"
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password("TelemetryTestPassword123!"),
                is_active=True,
                is_2fa_enabled=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        _, session_id = create_refresh_token(user_id=user.id, db=db)
        token = create_access_token(data={"sub": user.email, "session_id": session_id})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1. OpenTelemetry Initialization & Resource Attributes
# ---------------------------------------------------------------------------
def test_opentelemetry_initialization():
    """Verifies that OpenTelemetry initializes providers with correct metadata."""
    settings = get_settings()
    telemetry_manager.initialize()

    assert telemetry_manager._initialized is True
    if OPENTELEMETRY_AVAILABLE:
        tracer = telemetry_manager.get_tracer("test-tracer")
        assert tracer is not None

        meter = telemetry_manager.get_meter("test-meter")
        assert meter is not None


def test_telemetry_idempotent_instrumentation():
    """Verifies that setup_telemetry can be called multiple times without errors."""
    setup_telemetry(app, engine=engine)
    setup_telemetry(app, engine=engine)
    assert telemetry_manager._initialized is True


# ---------------------------------------------------------------------------
# 2. API Request Throughput & Latency Percentiles
# ---------------------------------------------------------------------------
def test_record_api_request_and_percentiles():
    """Verifies recording requests calculates min, max, average, and percentiles accurately."""
    # Record 100 simulated requests with known latencies: 1ms to 100ms
    for i in range(1, 101):
        latency_sec = i / 1000.0  # 0.001s to 0.100s
        status = 200 if i <= 90 else (400 if i <= 98 else 500)
        metrics_collector.record_api_request(
            method="GET",
            path="/contracts/123",  # should normalize to /contracts/{id}
            status_code=status,
            duration_seconds=latency_sec,
        )

    snapshot = metrics_collector.get_snapshot()

    # Request counts
    assert snapshot["requests"]["total"] == 100
    assert snapshot["requests"]["status_2xx"] == 90
    assert snapshot["requests"]["status_4xx"] == 8
    assert snapshot["requests"]["status_5xx"] == 2
    assert snapshot["requests"]["error_rate_pct"] == 10.0

    # Latency percentiles in milliseconds
    assert snapshot["latency_ms"]["min"] == 1.0
    assert snapshot["latency_ms"]["max"] == 100.0
    assert 48.0 <= snapshot["latency_ms"]["p50"] <= 52.0
    assert 93.0 <= snapshot["latency_ms"]["p95"] <= 97.0
    assert 97.0 <= snapshot["latency_ms"]["p99"] <= 100.0

    # Dynamic route normalization
    assert "GET /contracts/{id}" in snapshot["routes"]
    assert snapshot["routes"]["GET /contracts/{id}"]["count"] == 100


# ---------------------------------------------------------------------------
# 3. Database Query Duration Telemetry
# ---------------------------------------------------------------------------
def test_database_query_duration_tracking():
    """Verifies database query duration and slow query detection."""
    metrics_collector.record_db_query(0.005, "SELECT 1")
    metrics_collector.record_db_query(0.012, "SELECT * FROM users")
    metrics_collector.record_db_query(0.150, "SELECT * FROM contracts JOIN analyses...")  # slow query (> 100ms)

    snapshot = metrics_collector.get_snapshot()

    assert snapshot["database"]["total_queries"] == 3
    assert snapshot["database"]["slow_queries_count"] == 1
    assert snapshot["database"]["total_duration_seconds"] == pytest.approx(0.167, rel=1e-2)
    assert snapshot["database"]["avg_query_duration_ms"] > 50.0


# ---------------------------------------------------------------------------
# 4. Multi-Agent Contract Analysis Duration Tracking
# ---------------------------------------------------------------------------
def test_analysis_duration_tracking():
    """Verifies recording analysis workflow duration and success/failure ratios."""
    metrics_collector.record_analysis_duration(5.2, success=True, contract_id=1)
    metrics_collector.record_analysis_duration(6.8, success=True, contract_id=2)
    metrics_collector.record_analysis_duration(1.5, success=False, contract_id=3)

    snapshot = metrics_collector.get_snapshot()

    assert snapshot["analysis"]["total_workflows"] == 3
    assert snapshot["analysis"]["successful"] == 2
    assert snapshot["analysis"]["failed"] == 1
    assert 4.0 <= snapshot["analysis"]["avg_duration_seconds"] <= 5.0


# ---------------------------------------------------------------------------
# 5. Authentication Anomaly & Threat Level Telemetry
# ---------------------------------------------------------------------------
def test_auth_anomalies_and_threat_scoring():
    """Verifies that suspicious auth events escalate threat score from LOW to HIGH."""
    snapshot = metrics_collector.get_snapshot()
    assert snapshot["auth_telemetry"]["threat_level"] == "LOW"

    # Record normal logins
    metrics_collector.record_auth_success()
    metrics_collector.record_auth_success()

    # Record failed login attempts
    metrics_collector.record_auth_failure("invalid_credentials")
    metrics_collector.record_auth_failure("invalid_credentials")
    metrics_collector.record_auth_failure("invalid_credentials")
    metrics_collector.record_auth_failure("invalid_otp")
    metrics_collector.record_auth_failure("expired_otp")
    metrics_collector.record_auth_failure("rate_limit_exceeded")

    snapshot = metrics_collector.get_snapshot()
    assert snapshot["auth_telemetry"]["total_logins"] == 2
    assert snapshot["auth_telemetry"]["failed_logins"] == 3
    assert snapshot["auth_telemetry"]["failed_otp_attempts"] == 2
    assert snapshot["auth_telemetry"]["rate_limit_hits"] == 1
    assert snapshot["auth_telemetry"]["failures_by_reason"]["invalid_credentials"] == 3
    assert snapshot["auth_telemetry"]["failures_by_reason"]["invalid_otp"] == 1
    assert snapshot["auth_telemetry"]["failures_by_reason"]["expired_otp"] == 1

    # Escalate to HIGH threat level
    for _ in range(25):
        metrics_collector.record_auth_failure("invalid_credentials")

    snapshot_high = metrics_collector.get_snapshot()
    assert snapshot_high["auth_telemetry"]["threat_level"] == "HIGH"


# ---------------------------------------------------------------------------
# 6. GET /metrics Endpoint (Prometheus Text Format)
# ---------------------------------------------------------------------------
def test_prometheus_metrics_endpoint(client):
    """Verifies GET /metrics outputs standard Prometheus exposition format."""
    # Generate some traffic first
    client.get("/health")
    metrics_collector.record_auth_failure("invalid_credentials")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    content = response.text
    # Verify standard Prometheus headers and metrics
    assert "# HELP api_requests_total" in content
    assert "# TYPE api_requests_total counter"
    assert "api_requests_total" in content
    assert "# HELP api_request_duration_seconds" in content
    assert "# HELP db_queries_total" in content
    assert "# HELP analysis_workflows_total" in content
    assert "# HELP auth_failures_total" in content
    assert "# HELP system_uptime_seconds" in content


# ---------------------------------------------------------------------------
# 7. GET /metrics?format=json Endpoint (Structured JSON)
# ---------------------------------------------------------------------------
def test_json_metrics_endpoint(client):
    """Verifies GET /metrics?format=json returns structured telemetry snapshot."""
    client.get("/health")

    # Request via query param
    res_param = client.get("/metrics?format=json")
    assert res_param.status_code == 200
    assert "application/json" in res_param.headers["content-type"]
    data = res_param.json()

    assert "system" in data
    assert "requests" in data
    assert "latency_ms" in data
    assert "database" in data
    assert "analysis" in data
    assert "auth_telemetry" in data
    assert data["system"]["service"] == "legal-ai-platform"

    # Request via Accept header
    res_hdr = client.get("/metrics", headers={"Accept": "application/json"})
    assert res_hdr.status_code == 200
    assert "application/json" in res_hdr.headers["content-type"]


# ---------------------------------------------------------------------------
# 8. GET /admin/telemetry Protected Endpoint
# ---------------------------------------------------------------------------
def test_admin_telemetry_endpoint(client, auth_headers):
    """Verifies that /admin/telemetry requires authentication and returns snapshot."""
    # Unauthenticated request should be rejected
    unauth_res = client.get("/admin/telemetry")
    assert unauth_res.status_code == 401

    # Authenticated request should return 200 OK with telemetry
    auth_res = client.get("/admin/telemetry", headers=auth_headers)
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert "system" in data
    assert "auth_telemetry" in data
    assert "latency_ms" in data


# ---------------------------------------------------------------------------
# 9. GET /health Telemetry Status Linkage
# ---------------------------------------------------------------------------
def test_health_endpoint_includes_telemetry(client):
    """Verifies GET /health includes real-time telemetry state."""
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.json()

    assert payload["status"] == "ok"
    assert "telemetry" in payload
    assert payload["telemetry"]["active"] is True
    assert "total_requests" in payload["telemetry"]


# ---------------------------------------------------------------------------
# 10. Live HTTP Middleware Telemetry & X-Process-Time Header
# ---------------------------------------------------------------------------
def test_live_middleware_telemetry_recording(client):
    """Verifies that live requests pass through middleware and record into telemetry."""
    initial_count = metrics_collector.total_requests

    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Process-Time" in res.headers

    # Verify metrics_collector incremented
    assert metrics_collector.total_requests >= initial_count + 1
    assert metrics_collector.status_2xx >= 1


# ---------------------------------------------------------------------------
# 11. Thread Safety & Concurrent Recording
# ---------------------------------------------------------------------------
def test_metrics_collector_thread_safety():
    """Verifies that MetricsCollector handles concurrent multi-threaded writes without race conditions."""
    threads = []
    iterations_per_thread = 50

    def worker():
        for _ in range(iterations_per_thread):
            metrics_collector.record_api_request("GET", "/health", 200, 0.005)
            metrics_collector.record_db_query(0.002, "SELECT 1")
            metrics_collector.record_auth_failure("invalid_credentials")

    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    snapshot = metrics_collector.get_snapshot()
    assert snapshot["requests"]["total"] == 500
    assert snapshot["database"]["total_queries"] == 500
    assert snapshot["auth_telemetry"]["failed_logins"] == 500


# ---------------------------------------------------------------------------
# 12. Test Isolation and Reset
# ---------------------------------------------------------------------------
def test_metrics_collector_reset():
    """Verifies that reset zeroes all metrics."""
    metrics_collector.record_api_request("GET", "/test", 200, 0.01)
    metrics_collector.record_db_query(0.02)
    metrics_collector.record_auth_failure("test_reason")

    assert metrics_collector.total_requests == 1
    metrics_collector.reset()

    assert metrics_collector.total_requests == 0
    assert metrics_collector.total_db_queries == 0
    assert metrics_collector.failed_logins == 0
    assert len(metrics_collector.latencies) == 0
