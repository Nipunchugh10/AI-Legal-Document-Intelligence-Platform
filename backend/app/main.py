"""
AI Legal Document Intelligence Platform
========================================
FastAPI application entry point.

Day 2 — Health check endpoint, CORS, lifespan
Day 4 — Auth router registered (/auth/register, /auth/login, /auth/me)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import auth as auth_router

settings = get_settings()


# ------------------------------------------------------------------
# Lifespan: startup & shutdown events
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on application startup and shutdown."""
    print("=" * 60)
    print(" AI Legal Document Intelligence Platform")
    print(f" Environment : {settings.APP_ENV}")
    print(f" Debug       : {settings.DEBUG}")
    print(f" Started at  : {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    yield
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
# Routers — Day 4 (more routers added in subsequent days)
# ------------------------------------------------------------------
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])


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
    description="Sends a test prompt to the Google Gemini model to verify integration.",
)
async def test_llm(prompt: str = "Say 'Hello from Gemini'"):
    """
    Verifies the LLM Service and Gemini API Key are working.
    """
    from app.services.llm import get_llm_service
    from fastapi import HTTPException
    try:
        service = get_llm_service()
        response = service.generate_text(prompt)
        return {
            "status": "success",
            "model": service.model_name,
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
