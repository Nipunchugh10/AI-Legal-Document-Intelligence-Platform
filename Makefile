# ==============================================================================
# AI Legal Document Intelligence Platform — Orchestration Makefile
# ==============================================================================
# Day 49: Complete Docker Compose Setup
# Provides developer shortcuts for container orchestration, migrations,
# log inspection, and automated testing across the microservice stack.
# ==============================================================================

.PHONY: help up down down-v build up-build restart ps status \
        logs logs-backend logs-frontend logs-db \
        migrate shell-backend shell-db test-backend test-frontend test clean

# Default target displays help documentation
.DEFAULT_GOAL := help

help:
	@echo "================================================================================"
	@echo " AI Legal Document Intelligence Platform — Command Shortcuts"
	@echo "================================================================================"
	@echo " Docker Stack Management:"
	@echo "   make up              Start all containers in detached mode"
	@echo "   make up-build        Rebuild images and start all containers in detached mode"
	@echo "   make down            Stop and remove all containers, networks"
	@echo "   make down-v          Stop containers and purge persistent volumes (reset DB)"
	@echo "   make build           Build container images without starting"
	@echo "   make restart         Restart all running containers"
	@echo "   make ps / status     Display health and status of all container services"
	@echo ""
	@echo " Telemetry & Logs:"
	@echo "   make logs            Follow live aggregated logs for all services"
	@echo "   make logs-backend    Follow live logs from FastAPI backend container"
	@echo "   make logs-frontend   Follow live logs from React / Nginx frontend container"
	@echo "   make logs-db         Follow live logs from PostgreSQL database container"
	@echo ""
	@echo " Database & Migrations:"
	@echo "   make migrate         Apply pending Alembic database migrations"
	@echo "   make shell-backend   Open interactive bash terminal inside backend container"
	@echo "   make shell-db        Open interactive psql terminal inside PostgreSQL container"
	@echo ""
	@echo " Quality Assurance & Testing:"
	@echo "   make test            Run full test suite (backend pytest + frontend build)"
	@echo "   make test-backend    Run backend pytest regression test suite"
	@echo "   make test-frontend   Run frontend TypeScript and Vite production build check"
	@echo "   make clean           Remove temporary build artifacts, dangling images & caches"
	@echo "================================================================================"

# --- Stack Lifecycle ----------------------------------------------------------

up:
	docker-compose up -d

build:
	docker-compose build

up-build:
	docker-compose up -d --build

down:
	docker-compose down

down-v:
	docker-compose down -v

restart:
	docker-compose restart

ps:
	docker-compose ps

status: ps

# --- Logs & Monitoring --------------------------------------------------------

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f postgres

# --- Shells & Administration --------------------------------------------------

migrate:
	docker-compose exec backend alembic upgrade head

shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec postgres psql -U postgres -d legal_ai_db

# --- Testing & Quality --------------------------------------------------------

test-backend:
	@if [ -f backend/venv_linux/bin/pytest ]; then \
		backend/venv_linux/bin/pytest backend/tests/ -v; \
	elif [ -f backend/venv/Scripts/pytest.exe ]; then \
		backend/venv/Scripts/pytest.exe backend/tests/ -v; \
	else \
		pytest backend/tests/ -v; \
	fi

test-frontend:
	cd frontend && npm run build

test: test-backend test-frontend

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	docker-compose down --remove-orphans 2>/dev/null || true
