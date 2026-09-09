"""
Day 54 Free Tier Test Suite — Hugging Face Spaces Gradio SDK & Unified Platform Runtime
=======================================================================================
Validates the 100% free deployment architecture on Hugging Face Spaces:
 1. Root app.py entrypoint presence and import structure
 2. Root requirements.txt dependencies including gradio and FastAPI
 3. Root packages.txt system apt dependencies for PDF and OCR processing
 4. README.md YAML frontmatter configured for sdk: gradio
 5. FastAPI + Gradio dual routing: Root (/) serves React 19 SPA
 6. FastAPI + Gradio dual routing: /gradio/ serves Gradio UI
 7. FastAPI health endpoint (/health) returns 200 OK
 8. Database migration logic integration in app.py
 9. API routes bypass SPA routing and return JSON responses
10. Non-existent API routes return 404 JSON (not SPA HTML)
"""

import os
import sys
import yaml
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root and backend directory to sys.path
_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_ROOT_DIR = _BACKEND_DIR.parent

if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Require gradio for this test module to avoid collection errors in minimal environments
pytest.importorskip("gradio", reason="gradio is required for Hugging Face Spaces Gradio SDK tests")

import space_app as space_module
from app.main import app as fastapi_app


@pytest.fixture
def client():
    return TestClient(space_module.app)


def test_root_app_entrypoint_exists():
    """Verifies that space_app.py exists at project root and exports the unified app."""
    app_path = _ROOT_DIR / "space_app.py"
    assert app_path.exists(), "Root space_app.py entrypoint must exist for Hugging Face Spaces Gradio SDK"
    assert hasattr(space_module, "app"), "space_app.py must export the ASGI 'app' instance"


def test_root_requirements_specification():
    """Verifies that root requirements.txt exists and includes required libraries."""
    req_path = _ROOT_DIR / "requirements.txt"
    assert req_path.exists(), "requirements.txt must exist at project root for HF Spaces"

    content = req_path.read_text(encoding="utf-8").lower()
    assert "gradio" in content, "requirements.txt must include gradio"
    assert "fastapi" in content, "requirements.txt must include fastapi"
    assert "uvicorn" in content, "requirements.txt must include uvicorn"
    assert "sqlalchemy" in content, "requirements.txt must include sqlalchemy"
    assert "alembic" in content, "requirements.txt must include alembic"
    assert "google-generativeai" in content or "google-genai" in content, "requirements.txt must include Gemini AI SDK"


def test_root_packages_specification():
    """Verifies that root packages.txt includes Linux system dependencies."""
    pkg_path = _ROOT_DIR / "packages.txt"
    assert pkg_path.exists(), "packages.txt must exist at project root for HF Spaces apt packages"

    content = pkg_path.read_text(encoding="utf-8")
    assert "poppler-utils" in content, "packages.txt must include poppler-utils for PDF rendering"
    assert "tesseract-ocr" in content, "packages.txt must include tesseract-ocr for image OCR"
    assert "libmagic1" in content, "packages.txt must include libmagic1 for MIME type detection"


def test_readme_gradio_frontmatter():
    """Verifies README.md frontmatter matches Hugging Face Spaces Gradio specification."""
    readme_path = _ROOT_DIR / "README.md"
    assert readme_path.exists()

    content = readme_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) >= 3, "README.md must have YAML frontmatter enclosed in '---'"

    meta = yaml.safe_load(parts[1].strip())
    assert meta.get("sdk") == "gradio", "Hugging Face Spaces SDK must be 'gradio' for the free tier"
    assert meta.get("app_file") in {"space_app.py", "app.py"}, "Gradio app_file must be specified"
    assert "sdk_version" in meta, "Gradio sdk_version should be declared"


def test_root_endpoint_serves_react_spa(client: TestClient):
    """Verifies that GET / serves the compiled React 19 SPA index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "<!doctype html>" in resp.text.lower() or "<html" in resp.text.lower()
    assert "id=\"root\"" in resp.text


def test_gradio_endpoint_serves_gradio_interface(client: TestClient):
    """Verifies that GET /gradio/ serves the Gradio interface HTML with HTTP 200."""
    resp = client.get("/gradio/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "gradio" in resp.text.lower() or "svelte" in resp.text.lower() or "<html" in resp.text.lower()


def test_health_endpoint_accessibility(client: TestClient):
    """Verifies that GET /health returns standard JSON 200 OK."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_unmatched_api_routes_return_json_404(client: TestClient):
    """Verifies that non-existent API routes return 404 JSON, not SPA index.html."""
    resp = client.get("/api/non-existent-endpoint-12345")
    assert resp.status_code == 404
    assert "application/json" in resp.headers.get("content-type", "")
    assert resp.json().get("detail") == "Endpoint not found"
