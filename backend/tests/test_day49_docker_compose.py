"""
Day 49 Test Suite — Complete Docker Compose Setup
------------------------------------------------
Verifies:
1. docker-compose.yml Schema & Service Topology:
   - Valid YAML syntax and version.
   - All 4 core services configured: postgres, backend, frontend, pgadmin.
   - Exact port mappings per PLAN.md specification (frontend: 3000, backend: 8000, pgadmin: 5050, postgres: 5433/5432).
   - Healthcheck configurations on postgres, backend, and frontend.
   - Service dependency graph (backend -> postgres, frontend -> backend).
   - Named bridge network (legal_ai_network) connecting all services.
   - Persistent named volumes (postgres_data, chroma_data).
2. Backend Containerization Assets:
   - backend/Dockerfile structure (Python base, curl, volumes, entrypoint).
   - backend/entrypoint.sh script (executable, DB connectivity check, alembic upgrade head).
3. Frontend Containerization Assets:
   - frontend/Dockerfile multi-stage build (Node builder -> Nginx runner).
   - frontend/nginx.conf (SPA routing, /api/ reverse proxy, gzip, security headers).
4. Docker Context Optimization:
   - Root, backend, and frontend .dockerignore files.
5. Makefile Shortcuts:
   - Target declarations: up, down, logs, migrate, ps, test, etc.
6. CLI Configuration Verification:
   - docker-compose config validates without errors.

Day 49 — Complete Docker Compose Setup
"""

import os
import sys
import stat
import subprocess
import pytest
import yaml

# Root directory of the repository
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_docker_compose_file_exists_and_parses():
    """Verify docker-compose.yml exists and parses as valid YAML."""
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    assert os.path.isfile(compose_path), "docker-compose.yml must exist at project root"

    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "docker-compose.yml must parse to a dictionary"
    assert "version" in data, "docker-compose.yml must have a version field"
    assert "services" in data, "docker-compose.yml must have services defined"


def test_docker_compose_services_topology():
    """Verify all 4 core services are declared with proper configurations."""
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    required_services = {"postgres", "backend", "frontend", "pgadmin"}
    assert required_services.issubset(set(services.keys())), (
        f"Missing required services. Found: {list(services.keys())}, Expected: {required_services}"
    )

    # 1. PostgreSQL Service
    pg = services["postgres"]
    assert "image" in pg and "postgres:15" in pg["image"]
    assert "environment" in pg
    assert "healthcheck" in pg
    assert "pg_isready" in str(pg["healthcheck"]["test"])
    assert any("legal_ai_network" in str(net) for net in pg.get("networks", []))

    # 2. Backend Service
    backend = services["backend"]
    assert "build" in backend
    assert "depends_on" in backend
    assert "postgres" in backend["depends_on"]
    assert backend["depends_on"]["postgres"].get("condition") == "service_healthy"
    assert "healthcheck" in backend
    assert any("legal_ai_network" in str(net) for net in backend.get("networks", []))

    # 3. Frontend Service
    frontend = services["frontend"]
    assert "build" in frontend
    assert "depends_on" in frontend
    assert "backend" in frontend["depends_on"]
    assert frontend["depends_on"]["backend"].get("condition") == "service_healthy"
    assert "healthcheck" in frontend
    assert any("3000" in str(p) for p in frontend.get("ports", []))
    assert any("legal_ai_network" in str(net) for net in frontend.get("networks", []))

    # 4. pgAdmin Service
    pgadmin = services["pgadmin"]
    assert "image" in pgadmin and "pgadmin4" in pgadmin["image"]
    assert any("5050" in str(p) for p in pgadmin.get("ports", []))
    assert any("legal_ai_network" in str(net) for net in pgadmin.get("networks", []))


def test_docker_compose_networks_and_volumes():
    """Verify named bridge network and persistent data volumes exist."""
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    networks = data.get("networks", {})
    assert "legal_ai_network" in networks
    assert networks["legal_ai_network"].get("driver") == "bridge"

    volumes = data.get("volumes", {})
    assert "postgres_data" in volumes
    assert "chroma_data" in volumes


def test_backend_dockerfile_and_entrypoint():
    """Verify backend Dockerfile and entrypoint script."""
    dockerfile_path = os.path.join(REPO_ROOT, "backend", "Dockerfile")
    assert os.path.isfile(dockerfile_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "FROM python:3.11-slim" in content
    assert "curl" in content
    assert "requirements.txt" in content
    assert "ENTRYPOINT" in content
    assert "entrypoint.sh" in content

    entrypoint_path = os.path.join(REPO_ROOT, "backend", "entrypoint.sh")
    assert os.path.isfile(entrypoint_path)

    # Check executable permission
    st = os.stat(entrypoint_path)
    assert bool(st.st_mode & stat.S_IXUSR), "entrypoint.sh must be executable (chmod +x)"

    with open(entrypoint_path, "r", encoding="utf-8") as f:
        ep_content = f.read()

    assert "alembic upgrade head" in ep_content
    assert "psycopg2" in ep_content
    assert "exec \"$@\"" in ep_content


def test_frontend_dockerfile_and_nginx_conf():
    """Verify multi-stage frontend Dockerfile and custom Nginx SPA configuration."""
    dockerfile_path = os.path.join(REPO_ROOT, "frontend", "Dockerfile")
    assert os.path.isfile(dockerfile_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        df_content = f.read()

    assert "AS builder" in df_content
    assert "node:20-alpine" in df_content
    assert "npm run build" in df_content
    assert "AS runner" in df_content
    assert "nginx:1.25-alpine" in df_content
    assert "HEALTHCHECK" in df_content

    nginx_path = os.path.join(REPO_ROOT, "frontend", "nginx.conf")
    assert os.path.isfile(nginx_path)

    with open(nginx_path, "r", encoding="utf-8") as f:
        nginx_content = f.read()

    assert "try_files $uri $uri/ /index.html" in nginx_content
    assert "proxy_pass http://backend:8000/" in nginx_content
    assert "gzip on" in nginx_content
    assert "X-Frame-Options" in nginx_content


def test_dockerignore_files():
    """Verify root, backend, and frontend .dockerignore files prevent context bloat."""
    for path in [
        os.path.join(REPO_ROOT, ".dockerignore"),
        os.path.join(REPO_ROOT, "backend", ".dockerignore"),
        os.path.join(REPO_ROOT, "frontend", ".dockerignore"),
    ]:
        assert os.path.isfile(path), f"Missing .dockerignore at {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content.strip()) > 0


def test_makefile_shortcuts():
    """Verify root Makefile exists and contains all required targets."""
    makefile_path = os.path.join(REPO_ROOT, "Makefile")
    assert os.path.isfile(makefile_path)

    with open(makefile_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected_targets = [
        "up:",
        "down:",
        "logs:",
        "logs-backend:",
        "logs-frontend:",
        "logs-db:",
        "migrate:",
        "ps:",
        "build:",
        "help:",
        "clean:",
    ]
    for target in expected_targets:
        assert target in content, f"Makefile missing target: {target}"


def test_docker_compose_cli_validation():
    """Verify docker-compose config CLI command executes cleanly with exit code 0."""
    res = subprocess.run(
        ["docker-compose", "config"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"docker-compose config failed:\n{res.stderr}"
    assert "services:" in res.stdout
    assert "backend:" in res.stdout
    assert "frontend:" in res.stdout
    assert "postgres:" in res.stdout
    assert "pgadmin:" in res.stdout
