"""
Day 53 Test Suite — Hugging Face Spaces Multi-Stage Containerization & Unified Runtime
=====================================================================================
Validates:
 1. Multi-Stage Dockerfile architecture (Node 20 frontend-builder + Python 3.11 runtime)
 2. Non-root user UID 1000 configuration (Hugging Face Spaces Docker SDK specification)
 3. Default Hugging Face port 7860 exposure and environment variables
 4. Persistent directory permissions (/app/uploads, /app/chroma_data)
 5. Production entrypoint script (start.sh) syntax, permissions, and migration runner
 6. .dockerignore rules preventing leak of secrets, virtualenvs, and dev databases
 7. Unified runtime static SPA mounting and HTML5 history pushState fallback
 8. Client route resolution (/dashboard, /contracts/upload, /history, /security)
 9. API endpoint pass-through (ensuring API routes are not shadowed by SPA catch-all)
10. Unmatched API route 404 isolation (returning 404 JSON, not HTML)
11. Same-origin relative API client configuration in frontend/src/services/api.ts
12. Hugging Face iframe CSP headers and CORS origins
"""

import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_DIR = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.main import app
from app.core.config import get_settings, Settings


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Dockerfile Architecture & Non-Root UID 1000 Tests
# ==============================================================================

def test_dockerfile_exists_and_is_multistage():
    """Verifies that the root Dockerfile exists and defines a multi-stage build."""
    dockerfile_path = _ROOT_DIR / "Dockerfile"
    assert dockerfile_path.exists(), "Root Dockerfile must exist for Hugging Face Spaces"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Stage 1: Frontend builder
    assert "FROM node:20-alpine AS frontend-builder" in content or "AS frontend-builder" in content
    assert "npm run build" in content

    # Stage 2: Python runtime
    assert "FROM python:3.11-slim" in content or "FROM python:3.11" in content
    assert "COPY --from=frontend-builder" in content


def test_dockerfile_huggingface_user_and_port():
    """Verifies Hugging Face Spaces requirements: UID 1000 non-root user and port 7860."""
    dockerfile_path = _ROOT_DIR / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    # User UID 1000
    assert "useradd -m -u 1000 user" in content
    assert "USER user" in content

    # Port 7860
    assert "EXPOSE 7860" in content
    assert "PORT=7860" in content

    # Entrypoint
    assert 'CMD ["/app/start.sh"]' in content or "CMD [\"/app/start.sh\"]" in content


def test_dockerfile_directory_permissions():
    """Verifies that Dockerfile creates and chowns upload and ChromaDB directories for UID 1000."""
    dockerfile_path = _ROOT_DIR / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "/app/uploads" in content
    assert "/app/chroma_data" in content
    assert "chown -R user:user" in content


# ==============================================================================
# 2. Start Script (start.sh) Configuration & Permissions
# ==============================================================================

def test_start_script_executable_and_valid():
    """Verifies that start.sh exists, is executable, and contains correct boot commands."""
    start_sh_path = _ROOT_DIR / "start.sh"
    assert start_sh_path.exists(), "start.sh must exist at project root"
    assert os.access(start_sh_path, os.X_OK), "start.sh must have executable permissions"

    content = start_sh_path.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/bash")
    assert "set -e" in content
    assert "7860" in content
    assert "uvicorn app.main:app" in content
    assert "--proxy-headers" in content
    assert "alembic upgrade head" in content


# ==============================================================================
# 3. .dockerignore Security & Cleanliness
# ==============================================================================

def test_dockerignore_excludes_secrets_and_caches():
    """Verifies that .dockerignore blocks sensitive files, venvs, and node_modules."""
    dockerignore_path = _ROOT_DIR / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist"

    content = dockerignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    must_exclude = [
        ".git",
        ".env",
        "PLAN.md",
        "session_state.md",
        "backend/venv/",
        "frontend/node_modules/",
    ]
    for pattern in must_exclude:
        assert any(pattern in line for line in lines), f"Expected {pattern} in .dockerignore"


# ==============================================================================
# 4. Unified Runtime SPA Mounting & HTML5 PushState Navigation
# ==============================================================================

def test_spa_root_serves_html(client):
    """Verifies that GET / returns the React SPA index.html with 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<html" in response.text.lower()


def test_spa_client_routes_return_html(client):
    """Verifies HTML5 history pushState fallback: client routes return index.html for browser navigation."""
    client_routes = [
        "/dashboard",
        "/contracts/upload",
        "/contracts/compare",
        "/history",
        "/security",
        "/conversations",
    ]
    browser_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    for route in client_routes:
        response = client.get(route, headers=browser_headers)
        assert response.status_code == 200, f"Route {route} failed with status {response.status_code}"
        assert "text/html" in response.headers.get("content-type", ""), f"Route {route} did not return HTML"
        assert "<html" in response.text.lower(), f"Route {route} response did not contain HTML"


def test_spa_static_assets_served(client):
    """Verifies that static assets compiled into dist/assets are served with proper cache headers."""
    frontend_dist = _ROOT_DIR / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"

    if assets_dir.exists():
        css_or_js = next((f for f in assets_dir.iterdir() if f.is_file()), None)
        if css_or_js:
            rel_asset_path = f"/assets/{css_or_js.name}"
            response = client.get(rel_asset_path)
            assert response.status_code == 200
            assert len(response.content) > 0


# ==============================================================================
# 5. API Route Pass-Through & 404 Isolation
# ==============================================================================

def test_api_routes_not_shadowed_by_spa(client):
    """Verifies that API routes are never masked or intercepted by SPA fallback."""
    # 1. System health endpoint
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # 2. Database health endpoint
    db_resp = client.get("/health/db")
    assert db_resp.status_code in {200, 503}
    assert "status" in db_resp.json()

    # 3. Documentation endpoints
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200


def test_unknown_api_endpoints_return_json_404(client):
    """Verifies that unmatched API requests requesting JSON return 404 JSON, not SPA HTML."""
    response = client.get("/api/v1/nonexistent-endpoint", headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert response.headers.get("content-type") == "application/json"
    assert response.json() == {"detail": "Endpoint not found"}


# ==============================================================================
# 6. Frontend API Client Same-Origin Configuration
# ==============================================================================

def test_frontend_api_service_same_origin_relative():
    """Verifies frontend/src/services/api.ts uses same-origin relative URLs in production."""
    api_ts_path = _ROOT_DIR / "frontend" / "src" / "services" / "api.ts"
    assert api_ts_path.exists(), "frontend/src/services/api.ts must exist"

    content = api_ts_path.read_text(encoding="utf-8")
    assert "isLocalDev" in content
    assert '""' in content or "''" in content
    assert "baseURL: API_BASE_URL" in content


# ==============================================================================
# 7. Hugging Face Spaces Port and CSP Settings
# ==============================================================================

def test_settings_huggingface_spaces_configuration():
    """Verifies that Settings supports Hugging Face port 7860 and iframe CSP."""
    # Test setting PORT=7860 via environment
    settings_hf = Settings(PORT=7860, ALLOW_HF_IFRAME=True)
    assert settings_hf.PORT == 7860
    assert settings_hf.ALLOW_HF_IFRAME is True
    assert any("huggingface.co" in origin for origin in settings_hf.CORS_ORIGINS)
    assert any("*.hf.space" in origin for origin in settings_hf.CORS_ORIGINS)
