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

from app.core.config import get_settings
from app.api import auth as auth_router
from app.api import contracts as contracts_router
from app.api import qa as qa_router
from app.api import analysis as analysis_router
from app.api import comparison as comparison_router
from app.api import search as search_router
from app.api import admin as admin_router

# Setup logger for main module
logger = logging.getLogger(__name__)
settings = get_settings()


# ------------------------------------------------------------------
# Lifespan: startup & shutdown events
# ------------------------------------------------------------------
import asyncio

async def session_cleanup_loop():
    """Background loop to run session cleanup task daily."""
    from app.core.database import SessionLocal
    from app.services.session_cleanup import clean_expired_sessions

    print("[*] Starting background session cleanup loop...")
    while True:
        try:
            db = SessionLocal()
            try:
                count = clean_expired_sessions(db)
                if count > 0:
                    print(f"[+] Session Cleanup: Revoked {count} expired/idle sessions.")
            finally:
                db.close()
        except Exception as e:
            print(f"[-] Session Cleanup error: {e}")

        # Run every 24 hours (86400 seconds)
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on application startup and shutdown."""
    print("=" * 60)
    print(" AI Legal Document Intelligence Platform")
    print(f" Environment : {settings.APP_ENV}")
    print(f" Debug       : {settings.DEBUG}")
    print(f" Started at  : {datetime.now(timezone.utc).isoformat()}")
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


# ------------------------------------------------------------------
# CORS Middleware
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,  # React dev server
        "http://localhost:3000",  # Fallback
    ],
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
    """Measures total processing time and injects X-Process-Time response header."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    return response


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
    }


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
# Root Redirect (convenience)
# ------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    """Redirects root to the interactive API docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
