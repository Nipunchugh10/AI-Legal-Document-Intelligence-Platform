"""
OpenTelemetry & Production Observability Subsystem
-------------------------------------------------
Day 55 — Enterprise Telemetry, Metrics Tracking & Anomaly Monitoring

Provides:
- OpenTelemetry TracerProvider & MeterProvider configuration with standard resource attributes.
- Automatic FastAPI app instrumentation via FastAPIInstrumentor.
- Automatic SQLAlchemy engine instrumentation via SQLAlchemyInstrumentor.
- Database cursor latency telemetry hooks.
- High-performance, thread-safe real-time metrics aggregator (MetricsCollector):
  - Request latency percentiles (p50, p95, p99) and duration histograms.
  - Endpoint throughput and 2xx/4xx/5xx status distribution.
  - Database SQL query execution duration.
  - Multi-agent contract analysis pipeline duration.
  - Security & Authentication anomaly telemetry (failed logins, OTP brute-force attempts).
  - Prometheus exposition text formatting (/metrics) and structured JSON telemetry.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("app.telemetry")

# ---------------------------------------------------------------------------
# OpenTelemetry Core & SDK Imports (Safe Fallback)
# ---------------------------------------------------------------------------
try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.semconv.resource import ResourceAttributes

    OPENTELEMETRY_AVAILABLE = True
except Exception as _otel_err:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("OpenTelemetry SDK not fully available (%s). Running with in-memory telemetry.", _otel_err)


# ---------------------------------------------------------------------------
# In-Memory Metrics Collector & Aggregator
# ---------------------------------------------------------------------------
class MetricsCollector:
    """
    Thread-safe real-time operational metrics aggregator.
    Tracks API latency, request counts, errors, DB queries, analysis jobs, and auth anomalies.
    Exposes metrics in both structured JSON and Prometheus text format.
    """

    HISTOGRAM_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self):
        self._lock = threading.Lock()
        self.started_at = datetime.now(timezone.utc)
        self.reset()

    def reset(self) -> None:
        """Resets all telemetry counters and state."""
        with self._lock:
            # Request counts
            self.total_requests: int = 0
            self.status_2xx: int = 0
            self.status_3xx: int = 0
            self.status_4xx: int = 0
            self.status_5xx: int = 0

            # Requests by method + endpoint + status
            self.route_counts: Dict[str, int] = {}

            # Latencies per endpoint (in seconds)
            self.latencies: List[float] = []
            self.route_latencies: Dict[str, List[float]] = {}

            # Database query stats
            self.total_db_queries: int = 0
            self.total_db_duration: float = 0.0
            self.slow_db_queries: int = 0  # > 100ms
            self.db_latencies: List[float] = []

            # Analysis workflow stats
            self.total_analyses: int = 0
            self.successful_analyses: int = 0
            self.failed_analyses: int = 0
            self.analysis_durations: List[float] = []

            # Auth & Security anomalies
            self.total_logins: int = 0
            self.failed_logins: int = 0
            self.total_otp_attempts: int = 0
            self.failed_otp_attempts: int = 0
            self.rate_limit_hits: int = 0
            self.auth_failures_by_reason: Dict[str, int] = {}

            # General error classification
            self.errors_by_type: Dict[str, int] = {}

    # -----------------------------------------------------------------------
    # Recording Hooks
    # -----------------------------------------------------------------------
    def record_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Records an HTTP API request execution with latency and status code."""
        norm_method = method.upper()
        norm_path = self._normalize_path(path)
        route_key = f"{norm_method} {norm_path}"
        status_key = f"{norm_method} {norm_path} {status_code}"

        with self._lock:
            self.total_requests += 1

            if 200 <= status_code < 300:
                self.status_2xx += 1
            elif 300 <= status_code < 400:
                self.status_3xx += 1
            elif 400 <= status_code < 500:
                self.status_4xx += 1
            elif status_code >= 500:
                self.status_5xx += 1

            self.route_counts[status_key] = self.route_counts.get(status_key, 0) + 1

            # Keep rolling window of latencies (last 1,000 for aggregate, last 200 per route)
            self.latencies.append(duration_seconds)
            if len(self.latencies) > 1000:
                self.latencies.pop(0)

            if route_key not in self.route_latencies:
                self.route_latencies[route_key] = []
            self.route_latencies[route_key].append(duration_seconds)
            if len(self.route_latencies[route_key]) > 200:
                self.route_latencies[route_key].pop(0)

    def record_db_query(self, duration_seconds: float, statement: str = "") -> None:
        """Records database query execution time."""
        with self._lock:
            self.total_db_queries += 1
            self.total_db_duration += duration_seconds
            if duration_seconds >= 0.10:  # >= 100ms
                self.slow_db_queries += 1

            self.db_latencies.append(duration_seconds)
            if len(self.db_latencies) > 500:
                self.db_latencies.pop(0)

    def record_analysis_duration(
        self,
        duration_seconds: float,
        success: bool = True,
        contract_id: Optional[int] = None,
    ) -> None:
        """Records multi-agent contract analysis execution time."""
        with self._lock:
            self.total_analyses += 1
            if success:
                self.successful_analyses += 1
            else:
                self.failed_analyses += 1

            self.analysis_durations.append(duration_seconds)
            if len(self.analysis_durations) > 200:
                self.analysis_durations.pop(0)

    def record_auth_success(self) -> None:
        """Records a successful authentication."""
        with self._lock:
            self.total_logins += 1

    def record_auth_failure(self, reason: str, client_ip: str = "") -> None:
        """Records an authentication anomaly or failure (failed password, invalid OTP, rate limit)."""
        clean_reason = reason.strip().lower() if reason else "unknown"
        with self._lock:
            if clean_reason in {"invalid_credentials", "user_not_found", "bad_password"}:
                self.failed_logins += 1
            elif "otp" in clean_reason:
                self.failed_otp_attempts += 1
            elif "rate_limit" in clean_reason:
                self.rate_limit_hits += 1

            self.auth_failures_by_reason[clean_reason] = (
                self.auth_failures_by_reason.get(clean_reason, 0) + 1
            )

    def record_otp_attempt(self) -> None:
        """Records an OTP verification attempt."""
        with self._lock:
            self.total_otp_attempts += 1

    def record_error(self, error_type: str, status_code: int, endpoint: str) -> None:
        """Records an application error."""
        norm_path = self._normalize_path(endpoint)
        key = f"{error_type}:{status_code}:{norm_path}"
        with self._lock:
            self.errors_by_type[key] = self.errors_by_type.get(key, 0) + 1

    # -----------------------------------------------------------------------
    # Aggregation & Snapshots
    # -----------------------------------------------------------------------
    def get_snapshot(self) -> Dict[str, Any]:
        """Returns a comprehensive, structured JSON snapshot of operational telemetry."""
        settings = get_settings()
        now = datetime.now(timezone.utc)
        uptime = (now - self.started_at).total_seconds()

        with self._lock:
            total_reqs = self.total_requests
            err_count = self.status_4xx + self.status_5xx
            err_rate = round((err_count / total_reqs * 100), 2) if total_reqs > 0 else 0.0

            overall_latencies = sorted(self.latencies)
            p50 = round(self._percentile(overall_latencies, 50) * 1000, 2)
            p95 = round(self._percentile(overall_latencies, 95) * 1000, 2)
            p99 = round(self._percentile(overall_latencies, 99) * 1000, 2)
            avg_lat = (
                round((sum(self.latencies) / len(self.latencies)) * 1000, 2)
                if self.latencies
                else 0.0
            )
            min_lat = round(min(self.latencies) * 1000, 2) if self.latencies else 0.0
            max_lat = round(max(self.latencies) * 1000, 2) if self.latencies else 0.0

            avg_db_query = (
                round((self.total_db_duration / self.total_db_queries) * 1000, 2)
                if self.total_db_queries > 0
                else 0.0
            )

            avg_analysis_time = (
                round(sum(self.analysis_durations) / len(self.analysis_durations), 2)
                if self.analysis_durations
                else 0.0
            )

            # Calculate Suspicious Activity Threat Score
            suspicious_score = "LOW"
            if self.rate_limit_hits > 10 or self.failed_logins > 20 or self.failed_otp_attempts > 15:
                suspicious_score = "HIGH"
            elif self.rate_limit_hits > 2 or self.failed_logins > 5 or self.failed_otp_attempts > 5:
                suspicious_score = "MEDIUM"

            # Per-route summaries
            route_summaries = {}
            for route, lats in self.route_latencies.items():
                if lats:
                    route_summaries[route] = {
                        "count": len(lats),
                        "avg_ms": round((sum(lats) / len(lats)) * 1000, 2),
                        "p95_ms": round(self._percentile(sorted(lats), 95) * 1000, 2),
                    }

            return {
                "system": {
                    "service": settings.OTEL_SERVICE_NAME,
                    "version": settings.OTEL_SERVICE_VERSION,
                    "environment": settings.APP_ENV,
                    "uptime_seconds": round(uptime, 1),
                    "started_at": self.started_at.isoformat(),
                    "opentelemetry_active": OPENTELEMETRY_AVAILABLE and settings.OTEL_ENABLED,
                },
                "requests": {
                    "total": total_reqs,
                    "status_2xx": self.status_2xx,
                    "status_3xx": self.status_3xx,
                    "status_4xx": self.status_4xx,
                    "status_5xx": self.status_5xx,
                    "error_rate_pct": err_rate,
                },
                "latency_ms": {
                    "avg": avg_lat,
                    "min": min_lat,
                    "max": max_lat,
                    "p50": p50,
                    "p95": p95,
                    "p99": p99,
                },
                "database": {
                    "total_queries": self.total_db_queries,
                    "total_duration_seconds": round(self.total_db_duration, 4),
                    "avg_query_duration_ms": avg_db_query,
                    "slow_queries_count": self.slow_db_queries,
                },
                "analysis": {
                    "total_workflows": self.total_analyses,
                    "successful": self.successful_analyses,
                    "failed": self.failed_analyses,
                    "avg_duration_seconds": avg_analysis_time,
                },
                "auth_telemetry": {
                    "total_logins": self.total_logins,
                    "failed_logins": self.failed_logins,
                    "total_otp_attempts": self.total_otp_attempts,
                    "failed_otp_attempts": self.failed_otp_attempts,
                    "rate_limit_hits": self.rate_limit_hits,
                    "failures_by_reason": dict(self.auth_failures_by_reason),
                    "threat_level": suspicious_score,
                },
                "routes": route_summaries,
                "errors": dict(self.errors_by_type),
            }

    def get_prometheus_metrics(self) -> str:
        """
        Formats internal metrics into standard Prometheus exposition format (text/plain).
        Compatible with Prometheus, Grafana Cloud Agent, and Datadog scrapers.
        """
        snapshot = self.get_snapshot()
        lines: List[str] = []

        # Header metadata
        lines.append("# HELP api_requests_total Total number of HTTP API requests processed.")
        lines.append("# TYPE api_requests_total counter")
        with self._lock:
            if not self.route_counts:
                lines.append('api_requests_total{method="ALL",endpoint="ALL",status="ALL"} 0')
            else:
                for key, count in self.route_counts.items():
                    parts = key.split(" ")
                    if len(parts) >= 3:
                        m, p, s = parts[0], parts[1], parts[2]
                        lines.append(f'api_requests_total{{method="{m}",endpoint="{p}",status="{s}"}} {count}')

        lines.append("")
        lines.append("# HELP api_request_duration_seconds Latency of HTTP requests in seconds.")
        lines.append("# TYPE api_request_duration_seconds summary")
        lines.append(f'api_request_duration_seconds{{quantile="0.5"}} {snapshot["latency_ms"]["p50"] / 1000.0:.4f}')
        lines.append(f'api_request_duration_seconds{{quantile="0.95"}} {snapshot["latency_ms"]["p95"] / 1000.0:.4f}')
        lines.append(f'api_request_duration_seconds{{quantile="0.99"}} {snapshot["latency_ms"]["p99"] / 1000.0:.4f}')
        lines.append(f'api_request_duration_seconds_sum {sum(self.latencies):.4f}')
        lines.append(f'api_request_duration_seconds_count {snapshot["requests"]["total"]}')

        lines.append("")
        lines.append("# HELP db_queries_total Total database queries executed.")
        lines.append("# TYPE db_queries_total counter")
        lines.append(f'db_queries_total {snapshot["database"]["total_queries"]}')

        lines.append("")
        lines.append("# HELP db_query_duration_seconds_total Total duration of database queries in seconds.")
        lines.append("# TYPE db_query_duration_seconds_total counter")
        lines.append(f'db_query_duration_seconds_total {snapshot["database"]["total_duration_seconds"]}')

        lines.append("")
        lines.append("# HELP analysis_workflows_total Total multi-agent contract analysis executions.")
        lines.append("# TYPE analysis_workflows_total counter")
        lines.append(f'analysis_workflows_total{{status="success"}} {snapshot["analysis"]["successful"]}')
        lines.append(f'analysis_workflows_total{{status="failed"}} {snapshot["analysis"]["failed"]}')

        lines.append("")
        lines.append("# HELP auth_failures_total Total suspicious or failed authentication events.")
        lines.append("# TYPE auth_failures_total counter")
        with self._lock:
            if not self.auth_failures_by_reason:
                lines.append('auth_failures_total{reason="none"} 0')
            else:
                for reason, count in self.auth_failures_by_reason.items():
                    lines.append(f'auth_failures_total{{reason="{reason}"}} {count}')

        lines.append("")
        lines.append("# HELP rate_limit_hits_total Total times rate limiting throttled an incoming request.")
        lines.append("# TYPE rate_limit_hits_total counter")
        lines.append(f'rate_limit_hits_total {snapshot["auth_telemetry"]["rate_limit_hits"]}')

        lines.append("")
        lines.append("# HELP system_uptime_seconds Platform running duration in seconds.")
        lines.append("# TYPE system_uptime_seconds gauge")
        lines.append(f'system_uptime_seconds {snapshot["system"]["uptime_seconds"]}')

        return "\n".join(lines) + "\n"

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Groups dynamic IDs (/contracts/123 -> /contracts/{id}) to prevent cardinality explosion."""
        if not path:
            return "/"
        segments = path.split("?")[0].strip("/").split("/")
        norm_segments = []
        for seg in segments:
            if seg.isdigit():
                norm_segments.append("{id}")
            elif len(seg) > 20 and ("-" in seg or "_" in seg):
                norm_segments.append("{uuid}")
            else:
                norm_segments.append(seg)
        return "/" + "/".join(norm_segments)

    @staticmethod
    def _percentile(sorted_data: List[float], percentile: float) -> float:
        """Computes percentile from a pre-sorted array."""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1


# Global Singleton Metrics Collector
metrics_collector = MetricsCollector()


# ---------------------------------------------------------------------------
# OpenTelemetry Manager & Instrumentation Orchestrator
# ---------------------------------------------------------------------------
class TelemetryManager:
    """
    Manages OpenTelemetry TracerProvider, MeterProvider, and automatic instrumentors.
    """

    def __init__(self):
        self._initialized: bool = False
        self._tracer_provider: Optional[Any] = None
        self._meter_provider: Optional[Any] = None
        self._app_instrumented: bool = False
        self._db_instrumented: bool = False

    def initialize(self) -> None:
        """Initializes OpenTelemetry providers if not already configured."""
        if self._initialized:
            return

        settings = get_settings()
        if not settings.OTEL_ENABLED or not OPENTELEMETRY_AVAILABLE:
            logger.info("OpenTelemetry disabled or SDK unavailable. Telemetry running in in-memory mode.")
            self._initialized = True
            return

        try:
            resource = Resource.create(
                {
                    ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME,
                    ResourceAttributes.SERVICE_VERSION: settings.OTEL_SERVICE_VERSION,
                    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.APP_ENV,
                }
            )

            # Initialize TracerProvider
            self._tracer_provider = TracerProvider(resource=resource)
            otel_trace.set_tracer_provider(self._tracer_provider)

            # Initialize MeterProvider
            self._meter_provider = MeterProvider(resource=resource)
            otel_metrics.set_meter_provider(self._meter_provider)

            self._initialized = True
            logger.info(
                "OpenTelemetry initialized successfully (service=%s, env=%s).",
                settings.OTEL_SERVICE_NAME,
                settings.APP_ENV,
            )
        except Exception as e:
            logger.error("Failed to initialize OpenTelemetry providers: %s. Continuing fail-open.", e)
            self._initialized = True

    def get_tracer(self, name: str = "legal-ai-backend", version: str = "1.0.0"):
        """Returns an OpenTelemetry tracer instance."""
        if OPENTELEMETRY_AVAILABLE and self._tracer_provider:
            return self._tracer_provider.get_tracer(name, version)
        return otel_trace.get_tracer(name, version) if OPENTELEMETRY_AVAILABLE else None

    def get_meter(self, name: str = "legal-ai-metrics", version: str = "1.0.0"):
        """Returns an OpenTelemetry meter instance."""
        if OPENTELEMETRY_AVAILABLE and self._meter_provider:
            return self._meter_provider.get_meter(name, version)
        return otel_metrics.get_meter(name, version) if OPENTELEMETRY_AVAILABLE else None

    def instrument_fastapi(self, app: Any) -> None:
        """Instruments a FastAPI application instance."""
        if self._app_instrumented or not OPENTELEMETRY_AVAILABLE:
            return

        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self._tracer_provider,
                meter_provider=self._meter_provider,
                excluded_urls="health,health/db,metrics,favicon.ico,assets/*",
            )
            self._app_instrumented = True
            logger.info("FastAPI app instrumented with OpenTelemetry.")
        except Exception as e:
            logger.warning("Could not instrument FastAPI app with OpenTelemetry: %s", e)

    def instrument_sqlalchemy(self, engine: Any) -> None:
        """Instruments SQLAlchemy database engine with OpenTelemetry and query telemetry hooks."""
        if self._db_instrumented or engine is None:
            return

        # 1. OpenTelemetry SQLAlchemy auto-instrumentation
        if OPENTELEMETRY_AVAILABLE:
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

                SQLAlchemyInstrumentor().instrument(
                    engine=engine,
                    tracer_provider=self._tracer_provider,
                )
                logger.info("SQLAlchemy engine instrumented with OpenTelemetry.")
            except Exception as e:
                logger.warning("Could not instrument SQLAlchemy engine: %s", e)

        # 2. Database query latency recording hooks
        try:
            from sqlalchemy import event

            @event.listens_for(engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                if context:
                    setattr(context, "_query_start_time", time.perf_counter())

            @event.listens_for(engine, "after_cursor_execute")
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                start = getattr(context, "_query_start_time", None) if context else None
                if start is not None:
                    duration = time.perf_counter() - start
                    metrics_collector.record_db_query(duration, statement)

            self._db_instrumented = True
            logger.info("SQLAlchemy query latency event listener attached.")
        except Exception as e:
            logger.warning("Could not attach SQLAlchemy query event listener: %s", e)


# Global Telemetry Manager Singleton
telemetry_manager = TelemetryManager()


def setup_telemetry(app: Any, engine: Optional[Any] = None) -> None:
    """Convenience entrypoint to initialize OpenTelemetry, instrument FastAPI, and instrument SQLAlchemy."""
    telemetry_manager.initialize()
    if app is not None:
        telemetry_manager.instrument_fastapi(app)
    if engine is not None:
        telemetry_manager.instrument_sqlalchemy(engine)
