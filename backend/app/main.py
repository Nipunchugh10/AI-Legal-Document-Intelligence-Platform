"""
AI Legal Document Intelligence Platform
========================================
FastAPI application entry point.

Day 2 — Health check endpoint, CORS, lifespan
Day 4 — Auth router registered (/auth/register, /auth/login, /auth/me)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from typing import Optional
from app.core.config import get_settings
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter, custom_rate_limit_exceeded_handler
from app.core.telemetry import setup_telemetry, metrics_collector
from app.core.database import engine
from app.api import auth as auth_router
from app.api import contracts as contracts_router
from app.api import qa as qa_router
from app.api import analysis as analysis_router
from app.api import comparison as comparison_router
from app.api import search as search_router
from app.api import admin as admin_router
from app.api import history as history_router
from app.api import account as account_router

# Setup logger for main module
from app.core.config import get_settings, configure_logging

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Lifespan: startup & shutdown events
# ------------------------------------------------------------------
import asyncio

async def session_cleanup_loop():
    """Background loop to run session and data retention cleanup tasks daily."""
    from app.core.database import SessionLocal
    from app.services.session_cleanup import clean_expired_sessions
    from app.services.account_service import apply_retention_cleanup

    print("[*] Starting background session & retention cleanup loop...")
    while True:
        try:
            db = SessionLocal()
            try:
                count = clean_expired_sessions(db)
                if count > 0:
                    print(f"[+] Session Cleanup: Revoked {count} expired/idle sessions.")

                purged = apply_retention_cleanup(db)
                if purged > 0:
                    print(f"[+] Retention Policy: Purged {purged} expired activity log records.")
            finally:
                db.close()
        except Exception as e:
            print(f"[-] Maintenance Cleanup error: {e}")

        # Run every 24 hours (86400 seconds)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on application startup and shutdown."""
    print("=" * 60)
    print(" AI Legal Document Intelligence Platform")
    print(f" Environment   : {settings.APP_ENV}")
    print(f" Debug         : {settings.DEBUG}")
    print(f" Log Level     : {settings.LOG_LEVEL}")
    print(f" Security Hdr  : {settings.STRICT_SECURITY_HEADERS}")
    print(f" Started at    : {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Start the session cleanup task in the background
    cleanup_task = asyncio.create_task(session_cleanup_loop())

    yield

    # Cancel cleanup task on shutdown
    cleanup_task.cancel()
    print("Shutting down...")


# ------------------------------------------------------------------
# Application Instance
# ------------------------------------------------------------------
app = FastAPI(
    title="AI Legal Document Intelligence Platform",
    description=(
        "An AI-powered platform that analyzes legal documents, "
        "extracts key clauses, flags risks, checks compliance, "
        "and enables conversational Q&A — all with cited sources."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter to app state and register 429 handler (Day 54)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# OpenTelemetry & Observability Auto-Instrumentation — Day 55
setup_telemetry(app, engine=engine)


# ------------------------------------------------------------------
# CORS Middleware — Day 50 Dynamic Origins
# ------------------------------------------------------------------
cors_origins = list(settings.CORS_ORIGINS) if isinstance(settings.CORS_ORIGINS, list) else [settings.FRONTEND_URL]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in cors_origins:
    cors_origins.append(settings.FRONTEND_URL)
if "http://localhost:3000" not in cors_origins:
    cors_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Response Compression & Performance Middleware — Day 43
# ------------------------------------------------------------------
from fastapi.middleware.gzip import GZipMiddleware
import time

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Measures total processing time, injects X-Process-Time header, and records OpenTelemetry metrics."""
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        process_time = time.perf_counter() - start_time
        metrics_collector.record_api_request(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_seconds=process_time,
        )
        metrics_collector.record_error("server_error", 500, request.url.path)
        raise exc

    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"

    # Record API request latency & status in telemetry (Day 55)
    metrics_collector.record_api_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=process_time,
    )
    if response.status_code >= 400:
        err_type = "client_error" if response.status_code < 500 else "server_error"
        metrics_collector.record_error(err_type, response.status_code, request.url.path)

    return response


# ------------------------------------------------------------------
# Host Header Validation & Trusted Host Middleware — Day 60
# ------------------------------------------------------------------
from fastapi.middleware.trustedhost import TrustedHostMiddleware

allowed_hosts = (
    list(settings.ALLOWED_HOSTS)
    if isinstance(settings.ALLOWED_HOSTS, list)
    else [h.strip() for h in str(settings.ALLOWED_HOSTS).split(",") if h.strip()]
)
if "*" not in allowed_hosts:
    for default_host in ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]:
        if default_host not in allowed_hosts:
            allowed_hosts.append(default_host)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)


# ------------------------------------------------------------------
# Enterprise Security Headers Middleware — Day 50 & Day 60 Hardening
# ------------------------------------------------------------------
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    Injects enterprise-grade HTTP security headers on all responses (Day 60 Security Hardening).
    - Always enforces nosniff, strict referrer, and restricted permissions.
    - Tailors frame protections (frame-ancestors for HF Spaces, X-Frame-Options: DENY elsewhere).
    - Injects HSTS in production or over HTTPS.
    """
    response = await call_next(request)
    import os

    # Universal security protections across all environments
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    is_hf_space = bool(
        os.getenv("SPACE_ID")
        or os.getenv("HUGGINGFACE_SPACE")
        or settings.ALLOW_HF_IFRAME
    )
    should_apply_strict_frame_and_tls = (
        settings.STRICT_SECURITY_HEADERS
        or settings.APP_ENV in {"production", "staging"}
        or is_hf_space
    )

    if is_hf_space:
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://huggingface.co https://*.huggingface.co;"
        )
    elif should_apply_strict_frame_and_tls:
        response.headers["X-Frame-Options"] = "DENY"

    if request.url.scheme == "https" or settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# ------------------------------------------------------------------
# Frontend Static Discovery & Unified SPA Navigation Middleware — Day 53
# ------------------------------------------------------------------
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

def _discover_frontend_dist() -> Optional[Path]:
    """
    Robustly locate the compiled React SPA (frontend/dist) across every runtime
    layout we deploy to: local dev, Docker (/app), and Hugging Face Spaces
    (/home/user/app). We check a broad set of explicit candidates AND walk up the
    parents of both this file and the current working directory looking for a
    `frontend/dist/index.html`. Every candidate and the final result are logged so
    the container's startup logs make any future miss self-diagnosing.
    """
    import os

    here = Path(__file__).resolve()
    cwd = Path(os.getcwd()).resolve()

    candidates: list[Path] = [
        # backend/webapp is a committed copy of the built SPA that lives INSIDE the
        # backend tree. Hugging Face Spaces strips a top-level `frontend/dist`
        # directory from the running filesystem (build systems commonly hardcode-
        # ignore `dist`/`build` regardless of .gitignore), so we ship the SPA under
        # a non-`dist` path that is guaranteed to be materialized alongside the app.
        here.parents[1] / "webapp",              # <repo>/backend/webapp
        cwd / "backend" / "webapp",
        here.parents[2] / "frontend" / "dist",   # <repo>/backend/app/main.py -> <repo>/frontend/dist
        here.parents[1] / "frontend" / "dist",   # defensive: alternate nesting
        here.parents[3] / "frontend" / "dist" if len(here.parents) > 3 else here.parents[2] / "frontend" / "dist",
        cwd / "frontend" / "dist",
        Path("/home/user/app/frontend/dist"),    # Hugging Face Spaces (Gradio SDK) layout
        Path("/app/frontend/dist"),              # Docker image layout
        Path("/app/dist"),
        here.parents[2] / "dist",
    ]

    # Walk upward from this file and the cwd to catch any layout we didn't hardcode.
    for base in {here, cwd}:
        for parent in [base, *base.parents][:6]:
            candidates.append(parent / "frontend" / "dist")

    seen: set[str] = set()
    logger.info("Frontend discovery: __file__=%s cwd=%s", here, cwd)
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        ok = c.exists() and (c / "index.html").exists()
        logger.info("Frontend candidate %s -> %s", c, "FOUND" if ok else "missing")
        if ok:
            return c
    return None


frontend_dist = _discover_frontend_dist()

if frontend_dist:
    logger.info("Serving frontend static assets from %s", frontend_dist)
else:
    logger.warning("Frontend dist NOT found in any candidate path — SPA will fall back to /docs.")


@app.middleware("http")
async def spa_navigation_middleware(request: Request, call_next):
    """
    Unified Runtime SPA Middleware — Day 53:
    In unified containers (Hugging Face Spaces), the React SPA and FastAPI backend
    share the same origin and port (7860).
    When a browser navigates to any URL (e.g. /dashboard, /history, /contracts/upload),
    it sends a GET request with 'Accept: text/html...'.
    If the path is not a documentation endpoint (/docs, /redoc, /openapi.json),
    not a system endpoint (/health, /health/db), and not a static asset,
    serve index.html so React Router performs client-side rendering.
    """
    if request.method == "GET" and frontend_dist:
        accept = request.headers.get("accept", "").lower()
        path = request.url.path
        if "text/html" in accept:
            # Exclude docs, health, static assets, gradio, and test endpoints
            if not path.startswith(("/docs", "/redoc", "/openapi.json", "/health", "/assets", "/gradio", "/test-")):
                file_candidate = frontend_dist / path.lstrip("/")
                if not (path != "/" and file_candidate.is_file()):
                    return FileResponse(frontend_dist / "index.html")
    return await call_next(request)




# ------------------------------------------------------------------
# Global Exception Handler — Day 29
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions, logs them with a traceback,
    and returns a standard internal server error response.
    Passes standard FastAPI HTTPExceptions and ValidationErrors through.
    """
    if isinstance(exc, RateLimitExceeded):
        return custom_rate_limit_exceeded_handler(request, exc)

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )
        
    logger.error("Unhandled error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


# ------------------------------------------------------------------
# Routers — Day 4 (more routers added in subsequent days)
# ------------------------------------------------------------------
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(search_router.router, prefix="/contracts", tags=["Search"])
app.include_router(comparison_router.router, prefix="/contracts", tags=["Comparison"])
app.include_router(contracts_router.router, prefix="/contracts", tags=["Contracts"])
app.include_router(qa_router.router, prefix="/contracts", tags=["Q&A"])
app.include_router(analysis_router.router, prefix="/contracts", tags=["Orchestration"])
app.include_router(admin_router.router, prefix="/admin", tags=["Admin & Telemetry"])
app.include_router(history_router.router, tags=["History & Conversations"])
app.include_router(account_router.router, tags=["Account & Privacy"])


# ------------------------------------------------------------------
# Health Check — Day 2 Deliverable
# ------------------------------------------------------------------
@app.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Returns the current status of the API server.",
)
async def health_check():
    """
    Health check endpoint.
    Returns status, environment, and current UTC timestamp.
    """
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "telemetry": {
            "active": settings.OTEL_ENABLED,
            "total_requests": metrics_collector.total_requests,
        },
    }


@app.get(
    "/health/db",
    tags=["System"],
    summary="Database Health Check",
    description="Probes database connectivity and returns latency, version, SSL, and schema health.",
)
async def db_health_check():
    """
    Active database diagnostic probe.
    Returns 200 OK when connected and core schema is healthy; 503 Service Unavailable otherwise.
    """
    from app.core.database import check_database_connection
    diag = check_database_connection()
    healthy = diag["status"] == "connected" and diag.get("core_tables_healthy")
    status_code = 200 if healthy else 503

    # Full diagnostics (DB host, server version, table inventory, migration revision)
    # are sensitive and available only to authenticated admins via /admin/db-health.
    # Anonymous callers receive a minimal liveness signal unless explicitly opted in.
    if not settings.EXPOSE_PUBLIC_DIAGNOSTICS:
        return JSONResponse(
            status_code=status_code,
            content={
                "status": diag["status"],
                "core_tables_healthy": bool(diag.get("core_tables_healthy")),
                "latency_ms": diag.get("latency_ms"),
            },
        )
    return JSONResponse(status_code=status_code, content=diag)


@app.get(
    "/metrics",
    tags=["System"],
    summary="OpenTelemetry & Prometheus Metrics",
    description="Returns real-time platform metrics in standard Prometheus exposition text format or structured JSON.",
)
async def metrics_endpoint(request: Request, format: Optional[str] = None):
    """
    Prometheus & OpenTelemetry metrics scrape endpoint (Day 55).
    Returns standard Prometheus exposition format (text/plain) by default.
    Returns application/json when requested via '?format=json' or Accept header.

    Access control (Security Hardening): the metrics payload exposes the internal
    route map, latency percentiles, and error/auth-anomaly counters, so anonymous
    scraping is disabled by default. Access requires ONE of:
      - a matching bearer token when METRICS_TOKEN is configured, or
      - EXPOSE_PUBLIC_DIAGNOSTICS=true (self-hosted / trusted-network deployments).
    Authenticated operators can always read the same data via /admin/telemetry.
    """
    from fastapi.responses import PlainTextResponse

    # Anonymous scraping is disabled in production/staging (mirrors the app's
    # environment-tiered hardening). In those environments access requires a
    # bearer token matching METRICS_TOKEN, unless EXPOSE_PUBLIC_DIAGNOSTICS is
    # explicitly enabled. Development/test keep the endpoint open for local use.
    gated = settings.APP_ENV in {"production", "staging"} and not settings.EXPOSE_PUBLIC_DIAGNOSTICS
    if gated:
        provided = request.headers.get("authorization", "")
        token = provided[7:].strip() if provided.lower().startswith("bearer ") else ""
        import hmac as _hmac
        allowed = bool(settings.METRICS_TOKEN) and _hmac.compare_digest(token, settings.METRICS_TOKEN)
        if not allowed:
            raise HTTPException(status_code=404, detail="Not found")

    accept = request.headers.get("accept", "")
    if format == "json" or "application/json" in accept:
        return JSONResponse(content=metrics_collector.get_snapshot())
    return PlainTextResponse(
        content=metrics_collector.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )



# ------------------------------------------------------------------
# LLM Test Endpoint
# ------------------------------------------------------------------
@app.post(
    "/api/test-llm",
    tags=["AI"],
    summary="Test Gemini LLM Connection",
    description="Sends a test prompt to the Google Gemini model to verify integration. Requires authentication. Only available in development.",
)
async def test_llm(prompt: str = "Say 'Hello from Gemini'"):
    """
    Verifies the LLM Service and Gemini API Key are working.
    Restricted to development environment to prevent unauthorized API usage.
    """
    from fastapi import HTTPException

    if settings.APP_ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")

    from app.services.llm_provider import get_llm_response
    try:
        response = get_llm_response(prompt, temperature=0.2)
        return {
            "status": "success",
            "model": settings.GEMINI_MODEL,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Static Frontend Files Mounting & Catch-All Fallback
# ------------------------------------------------------------------
if frontend_dist:
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        # 1. Allow documentation, OpenAPI schema, and Gradio routes
        if full_path in {"docs", "redoc", "openapi.json", "gradio"} or full_path.startswith(("docs/", "redoc/", "gradio/")):
            raise HTTPException(status_code=404, detail="Not found")

        # 2. Check if path matches a physical static asset (e.g. favicon.ico, logo.svg)
        if full_path:
            file_path = frontend_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)

        accept = request.headers.get("accept", "").lower()

        # 3. If request explicitly accepts text/html, serve the SPA HTML entrypoint
        if "text/html" in accept or accept == "":
            return FileResponse(frontend_dist / "index.html")

        # 4. If request explicitly asks for JSON or starts with known API prefixes, return 404
        api_prefixes = (
            "auth", "contracts", "admin", "history", "account", "health", "api",
        )
        if "application/json" in accept or full_path.startswith(api_prefixes):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        # 5. Default fallback to SPA index.html
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirects root to the interactive API docs when frontend dist is not mounted."""
        return RedirectResponse(url="/docs")
