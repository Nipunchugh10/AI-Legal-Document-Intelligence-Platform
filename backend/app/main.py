"""
AI Legal Document Intelligence Platform
========================================
FastAPI application entry point.

Day 2 Deliverable:
    - Health check endpoint at GET /health
    - CORS middleware for frontend connection
    - Lifespan event for startup/shutdown logging
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

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
# Root Redirect (convenience)
# ------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    """Redirects root to the interactive API docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
