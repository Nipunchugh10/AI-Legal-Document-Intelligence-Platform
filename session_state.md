**NOTE : THIS FILE WILL ALWAYS REMAIN IN gitignore, never push it on the github repository**
**NOTE : ALWAYS REMEBER THAT YOU ARE WORKING ON AN APPLICATION THAT IS SUPPOSED TO BE ABLE TO WORK PROPERLLY ON PRODUCTION SCALE AND CAN HANDLE LARGE NUMBER OF USERS SMOOTHLY, THE DATA PROTECTION MUST BE ROBUST AND CODE SHOULD BE OPTIMIZED**

# AI Legal Document Intelligence Platform - Session State Ledger

This ledger serves as the single source of truth for tracking daily progress, session-by-session achievements, and state transitions throughout the 62-day build plan.

---

## 📊 Overall Progress Tracker

- **Current Phase:** Phase 2A — Identity, Sessions, and Email-Based 2FA (Days 8–15)
- **Current Day:** Day 15 ⏳ (Up Next)
- **Overall Completion:** `23%` (14 of 62 days fully complete)
- **Active Branch:** `main` (pushed to GitHub: [Nipunchugh10/AI-Legal-Document-Intelligence-Platform](https://github.com/Nipunchugh10/AI-Legal-Document-Intelligence-Platform))
- **Last Updated:** 2026-07-09

| Phase | Days | Focus | Status | Progress |
| :--- | :---: | :--- | :---: | :---: |
| **Phase 1 — Foundation & Project Setup** | 1–7 | Repo, FastAPI, DB Models, JWT Auth, Docker | ✅ Complete | `100%` |
| **Phase 2A — Identity, Sessions, and Email-Based 2FA** | 8–15 | Email OTP Auth, Session Expiry, Auto-logout | ✅ Complete | `100%` |
| **Phase 2B — Document Parsing Agent** | 16–22 | PDF Extraction, Chunking, Embeddings, LangGraph Agents 1–2 | ⏳ Pending | `0%` |
| **Phase 3 — Risk and Compliance Agents** | 23–29 | Agents 3–5, RAG Knowledge Base, Orchestration, Observability | ⏳ Pending | `0%` |
| **Phase 4 — Frontend Development** | 30–39 | Dashboard, Viewer, Risk Panels, Q&A Chat, Comparison UI | ⏳ Pending | `0%` |
| **Phase 5 — Contract Memory and Search** | 40–44 | Semantic Search, Async Pipeline, AI Stack Resilience | ⏳ Pending | `0%` |
| **Phase 6 — Activity History & Conversation Architecture**| 45–48 | User Sessions Log, Q&A History, Audit Logs, Data Export | ⏳ Pending | `0%` |
| **Phase 7 — DevOps and Deployment** | 49–55 | Docker, CI/CD, Cloud Deploy, Rate Limiting, Monitoring | ⏳ Pending | `0%` |
| **Phase 8 — Testing, Polish, and Documentation** | 56–62 | Tests, Prompt Tuning, Security Hardening, Docs, Launch | ⏳ Pending | `0%` |

---

## 🪵 Session Logs

### Day 0 — Ledger Initialization (2026-06-21)
> **Goal:** Create the session ledger to prepare for the 62-day build plan.
- **Achievements:**
  - Created `session_state.md` to act as the central ledger for tracking work.
  - Reviewed [PLAN.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/PLAN.md) structure.
- **Files Created:**
  - [session_state.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/session_state.md)
- **Files Modified:** None
- **System State:**
  - Database: Uninitialized
  - Backend: Uninitialized
  - Frontend: Uninitialized
- **Next Steps:**
  - Begin Day 1 and Day 2.

---

### Day 1 — Project Architecture and Repository Setup (2026-06-21) ✅
> **Goal:** Understand the full system before writing a single line of code. Create repository structure.
- **Achievements:**
  - Created complete project folder structure matching PLAN.md specification
  - Created professional README.md with architecture diagram, tech stack table, setup instructions
  - Created `.env.example` with all planned environment variables (DB, JWT, SMS, AI, Vector DB, Upload)
  - Created `.gitignore` covering Python, Node, environment files, uploads, ChromaDB, IDE/OS files
  - Created all `__init__.py` placeholder files across backend modules
  - Created `frontend/package.json` stub and `.gitkeep` files
- **Files Created:**
  - [README.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/README.md)
  - [.env.example](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.env.example)
  - [.gitignore](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.gitignore)
  - All `backend/app/**/__init__.py` placeholder files
  - `backend/uploads/.gitkeep`, `frontend/src/.gitkeep`
  - [frontend/package.json](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/package.json)
- **Deliverable:** ✅ Clean project with full folder structure ready and committed to GitHub.

---

### Day 2 — Backend Project Initialization (2026-06-21) ✅
> **Goal:** Get a working FastAPI project running locally.
- **Achievements:**
  - Created Python virtual environment using **CPython 3.11** (from python.org)
  - Installed all core dependencies successfully via pip
  - Created `main.py` with health check endpoint, CORS middleware, lifespan events, root redirect to docs
  - Created `core/config.py` with pydantic-settings loading all env vars from `.env`
  - Created `core/database.py` with SQLAlchemy engine, session factory, and `get_db` FastAPI dependency
  - Created `core/security.py` stub with bcrypt password hashing utilities
  - Created `.env` local development file (gitignored)
  - Created `backend/app/services/llm.py` — the `LLMService` class wrapping Google Gemini SDK
  - Added `/api/test-llm` test endpoint to `main.py`
  - Configured and **verified** Google Gemini API credentials end-to-end:
    - API Key: `AQ.Ab8RN6...` (new Google AI Studio key format, correctly identified)
    - Model: **`gemini-3.5-flash`** (confirmed available and responding in ListModels)
    - Integration test result: `Response: BackendWorks` ✅ SUCCESS
  - Switched from Zhipu AI/Z.AI (rate-limited, unreliable) to **Google Gemini 3.5 Flash** as the primary LLM throughout the project
  - Initialized local Git repository, ensured sensitive files remain gitignored
  - Created the public GitHub repository and successfully pushed the initial commit
  - **Verified:** Server starts successfully, `GET /health` returns `{"status": "ok"}` ✅
- **Files Created:**
  - [backend/requirements.txt](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/requirements.txt)
  - [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py)
  - [backend/app/core/config.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/config.py)
  - [backend/app/core/database.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/database.py)
  - [backend/app/core/security.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/security.py)
  - [backend/app/services/llm.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/llm.py)
  - [.env](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.env) (gitignored)
  - `backend/venv/` (CPython 3.11 virtual environment)
- **Files Modified:**
  - [README.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/README.md)
  - [.env.example](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.env.example) — updated to Gemini keys
- **Deliverable:** ✅ FastAPI running with `/health` returning `{"status": "ok"}`. Gemini 3.5 Flash LLM integration verified working end-to-end.

---

### Day 3 — Database Design and Migrations (2026-06-22) ✅
> **Goal:** Design and create all database tables via Alembic, including tables needed for sessions and history.

- **Achievements:**
  - Initialized Alembic in the `backend/` directory (`alembic init alembic`).
  - Configured `alembic/env.py` to dynamically load `DATABASE_URL` from `.env` and import all models for autogenerate schema detection.
  - Created 4 SQLAlchemy ORM models in `backend/app/models/` using SQLAlchemy 2.0 type-annotated `Mapped` / `mapped_column` syntax:
    - `User` (`users` table): `id`, `email`, `hashed_password`, `is_active`, `created_at`
    - `Contract` (`contracts` table): `id`, `user_id`, `filename`, `upload_path`, `status`, `created_at`
    - `Analysis` (`analyses` table): `id`, `contract_id`, `analysis_type`, `result_json` (JSONB), `created_at`
    - `AuditLog` (`audit_logs` table): `id`, `user_id` (nullable with set-null), `action`, `resource_id`, `metadata_json` (JSONB), `timestamp`
  - Generated initial autogenerated Alembic migration revision: `c65c3a39acec_initial_schema`.
  - Executed migration successfully (`alembic upgrade head`) to create the schemas in PostgreSQL database `legal_ai_db`.
  - Verified creation of tables (`users`, `contracts`, `analyses`, `audit_logs`, `alembic_version`) using `psql`.
- **Files Created:**
  - [backend/app/models/__init__.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/__init__.py)
  - [backend/app/models/user.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/user.py)
  - [backend/app/models/contract.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/contract.py)
  - [backend/app/models/analysis.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/analysis.py)
  - [backend/app/models/audit_log.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/audit_log.py)
  - [backend/alembic/env.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/alembic/env.py)
  - [backend/alembic.ini](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/alembic.ini)
  - [backend/alembic/versions/c65c3a39acec_initial_schema.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/alembic/versions/c65c3a39acec_initial_schema.py)
- **Deliverable:** ✅ PostgreSQL database `legal_ai_db` with 4 core tables created and verified. Alembic tracking enabled.

---

### Day 4 — Basic Authentication System (2026-06-22) ✅
> **Goal:** Build the first version of JWT-based login. (Will be upgraded with sessions and 2FA in Phase 2A.)

- **Achievements:**
  - Completed `core/security.py` (replacing Day 2 stub):
    - `hash_password` / `verify_password` via `passlib[bcrypt]`
    - `create_access_token(data, expires_delta)` — HS256 JWT, default 30 min TTL
    - `decode_access_token(token)` — returns payload dict or `None` on invalid/expired
    - `get_current_user(token, db)` — FastAPI dependency using `OAuth2PasswordBearer`; raises `401` on missing/bad token or inactive user
  - Created `app/schemas/auth.py` with 4 Pydantic models:
    - `RegisterRequest` (email: EmailStr, password: str min_length=8)
    - `LoginRequest` (email: EmailStr, password: str)
    - `TokenResponse` (access_token, token_type)
    - `UserResponse` (id, email, is_active, created_at; `from_attributes=True`)
  - Created `app/schemas/__init__.py` package init
  - Created `app/api/auth.py` with 3 endpoints:
    - `POST /auth/register` → 201 Created; bcrypt hash; email uniqueness enforced; returns `UserResponse`
    - `POST /auth/login` → 200 OK; generic `"Invalid credentials"` error (prevents user enumeration); returns `TokenResponse`
    - `GET /auth/me` → 200 OK; protected by `get_current_user` dependency; returns `UserResponse`
  - Registered auth router in `main.py`: `prefix="/auth"`, `tags=["Authentication"]`
  - **Fixed bcrypt 5.x / passlib 1.7.4 incompatibility**: downgraded `bcrypt` from `5.0.0` to `4.2.1`; pinned in `requirements.txt`
  - Installed `email-validator==2.3.0` for Pydantic `EmailStr` support; added to `requirements.txt`
  - **All 7 endpoint tests passed** (live against running server):
    1. ✅ `POST /auth/register` → `201` user created (id=1, email, is_active, created_at)
    2. ✅ `POST /auth/register` duplicate email → `400 "Email already registered"`
    3. ✅ `POST /auth/login` valid creds → `200` JWT token returned
    4. ✅ `POST /auth/login` wrong password → `401 "Invalid credentials"`
    5. ✅ `GET /auth/me` with valid token → `200` user profile
    6. ✅ `GET /auth/me` no token → `401`
    7. ✅ `GET /auth/me` invalid token → `401`
  - Committed 19 files as `fe1ff4c` and pushed to GitHub
- **Files Created:**
  - [backend/app/schemas/__init__.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/__init__.py)
  - [backend/app/schemas/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/auth.py)
  - [backend/app/api/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/auth.py)
- **Files Modified:**
  - [backend/app/core/security.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/security.py) — full JWT + dependency implementation
  - [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py) — auth router registered
  - [backend/requirements.txt](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/requirements.txt) — bcrypt pinned + email-validator added
- **Deliverable:** ✅ `POST /auth/register` creates a user. `POST /auth/login` returns a signed JWT. `GET /auth/me` rejects tokenless requests with `401`. All 7 tests pass.

---

### Day 5 — File Upload System (2026-06-28) ✅
> **Goal:** Accept PDF uploads, validate size/type, save to disk, and record in DB.
- **Achievements:**
  - Created `ContractResponse` Pydantic schema in [backend/app/schemas/contract.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/contract.py) and registered it in schemas package.
  - Implemented file upload router in [backend/app/api/contracts.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/contracts.py) with 3 endpoints:
    - `POST /contracts/upload`: Accepts files, enforces PDF extension check, validates file size (limit to 10MB via settings), generates UUID filename to prevent collisions, saves to disk under `uploads/`, writes metadata to DB `contracts` table.
    - `GET /contracts/`: Lists all contracts for currently authenticated user.
    - `GET /contracts/{contract_id}`: Retrieves details of a specific contract owned by the current user.
  - Registered contracts router in `backend/app/main.py` under the `/contracts` prefix.
  - Added end-to-end integration tests in [backend/tests/test_contracts.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_contracts.py) and verified size limit, type checks, listing, and data isolation.
- **Files Created:**
  - [backend/app/schemas/contract.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/contract.py)
  - [backend/app/api/contracts.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/contracts.py)
  - [backend/tests/test_contracts.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_contracts.py)
- **Files Modified:**
  - [backend/app/schemas/__init__.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/__init__.py)
  - [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py)
- **Deliverable:** ✅ PDF uploads work via Postman/tests, file stored under `uploads/`, record inserted in DB. Enforces size limit, file format validation, and user data isolation.

---

### Day 6 — Docker Setup (2026-06-28) ✅
> **Goal:** Containerize the entire backend stack (FastAPI, PostgreSQL 15, and pgAdmin).
- **Achievements:**
  - Created [backend/Dockerfile](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/Dockerfile) using `python:3.11-slim` with proper compilation dependencies installed (build-essential, libpq-dev).
  - Created [docker-compose.yml](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/docker-compose.yml) in the project root containing:
    - `postgres`: PostgreSQL 15 running on port 5432 with health check and persisted volume.
    - `backend`: FastAPI backend building from `backend/Dockerfile` with environmental config matching `.env`.
    - `pgadmin`: pgAdmin 4 running on port 8080.
- **Files Created:**
  - [backend/Dockerfile](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/Dockerfile)
  - [docker-compose.yml](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/docker-compose.yml)
- **Deliverable:** ✅ Complete Docker setup ready to be launched with `docker-compose up` to run backend + DB stack.

---

### Day 7 — Frontend Project Initialization (2026-06-28) ✅
> **Goal:** Scaffolding the React + TypeScript frontend and connecting auth.
- **Achievements:**
  - Initialized a React + TypeScript project in the `frontend` folder using Vite.
  - Installed core runtime libraries: `axios`, `react-router-dom`, `@tanstack/react-query`, `zustand`, and `react-hook-form`.
  - Built a comprehensive global design stylesheet in [frontend/src/index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css) using Vanilla CSS for high-fidelity dark-mode customization (Outfit/Jakarta fonts, glassmorphism, glowing borders, premium buttons, input focus states).
  - Created Axios service in [frontend/src/services/api.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/services/api.ts) with interceptors to automatically attach JWT header on requests and redirect on `401` session expiry.
  - Created Zustand state store in [frontend/src/store/useAuthStore.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/store/useAuthStore.ts) to manage user identity and active sessions.
  - Created `/login` page in [frontend/src/pages/Login.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Login.tsx) with validation and loader states.
  - Created `/register` page in [frontend/src/pages/Register.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Register.tsx) with email check and password match validations.
  - Created a rich `/dashboard` workspace page in [frontend/src/pages/Dashboard.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Dashboard.tsx) showing real uploaded contracts (fetched via Day 5 listing endpoint), featuring an interactive PDF file upload zone, status badges, and sign out controls.
  - Configured router and auth guards in [frontend/src/App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx).
  - Verified frontend builds successfully with `npm run build` and has zero TS compile errors.
- **Files Created:**
  - [frontend/src/services/api.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/services/api.ts)
  - [frontend/src/store/useAuthStore.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/store/useAuthStore.ts)
  - [frontend/src/pages/Login.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Login.tsx)
  - [frontend/src/pages/Register.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Register.tsx)
  - [frontend/src/pages/Dashboard.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Dashboard.tsx)
- **Files Modified:**
  - [frontend/src/index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css)
  - [frontend/src/App.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.css)
  - [frontend/src/App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx)
- **Deliverable:** ✅ Login form redirects to protected workspace dashboard. Token is securely managed. Document list and upload panel successfully integrate with Day 5 FastAPI endpoints.

---

### Day 8 — Session Architecture Design (2026-06-28) ✅
> **Goal:** Design the multi-device user session and token refresh architecture.
- **Achievements:**
  - Created [ARCHITECTURE.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/ARCHITECTURE.md) in the project root containing specifications for database-backed user sessions, refresh token verification, auto-logout thresholds, and multi-agent workflow.
  - Specified short-lived JWT access tokens (15-min TTL) combined with database-backed refresh tokens (7-day TTL) for multi-device compatibility and secure token revocation.
  - Outlined auto-logout rules: 15-minute client-side inactivity monitoring, backend `SESSION_EXPIRED` response interceptor, and absolute 7-day limits.
  - Formulated the `user_sessions` database table structure.
- **Files Created:**
  - [ARCHITECTURE.md](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/ARCHITECTURE.md)
- **Deliverable:** ✅ Detailed security and session design completed and documented in ARCHITECTURE.md.

---

### Day 9 — Refresh Token Backend Implementation (2026-07-06) ✅
> **Goal:** Replace the simple JWT-only login with a proper access + refresh token system.
- **Achievements:**
  - Created the `user_sessions` database table and generated + applied Alembic migration `589ef280e83a_add_user_sessions_table.py` successfully.
  - Implemented `create_refresh_token(user_id, db, device_info, ip_address)` in `backend/app/core/security.py` using cryptographically secure random token hex strings hashed with SHA-256 at rest.
  - Updated configuration settings to enforce 15-minute access token lifetimes and 7-day refresh token lifetimes.
  - Updated `POST /auth/login` to capture client IP/User-Agent and issue both tokens (updating database `user_sessions`).
  - Added `POST /auth/refresh` supporting token rotation (exchanges valid refresh token for a new access token and a fresh rotated refresh token, revoking the old one).
  - Added `POST /auth/logout` revoking the current session's refresh token by setting `is_revoked = True` in the database.
  - Wrote a new automated API integration test suite in [backend/tests/test_auth_refresh.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_auth_refresh.py) verifying registration, login, token refresh, token rotation security, logout, and post-logout rejection.
  - Verified all tests passed successfully with uvicorn server running locally.
- **Files Created:**
  - [backend/app/models/user_session.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/models/user_session.py)
  - [backend/tests/test_auth_refresh.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/tests/test_auth_refresh.py)
  - `backend/alembic/versions/589ef280e83a_add_user_sessions_table.py` (Alembic migration)
- **Files Modified:**
  - [backend/app/models/__init__.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/models/__init__.py)
  - [backend/app/core/config.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/core/config.py)
  - [backend/app/core/security.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/core/security.py)
  - [backend/app/api/auth.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/api/auth.py)
  - [backend/app/schemas/auth.py](file:///C:/Users/Lenovo/Downloads/Old One Drive/AI Legal Document Intelligence Platform/backend/app/schemas/auth.py)
- **Deliverable:** ✅ Login returns both tokens. `/auth/refresh` issues rotated access and refresh tokens. `/auth/logout` revokes sessions. Integration test suite verified 100% success.

---

### Day 10 — Auto-Logout on Inactivity (Backend Support) (2026-07-06) ✅
> **Goal:** Make the backend aware of session activity so idle sessions can be expired.
- **Achievements:**
  - Updated access token structure to encode `session_id` inside the JWT payload on login and refresh.
  - Configured `SESSION_IDLE_TIMEOUT_MINUTES = 15` in `config.py`.
  - Modified the `get_current_user` FastAPI dependency to query the active database session:
    - Enforces 15-minute idle inactivity timeout against `last_active_at`.
    - Enforces 7-day absolute session timeout against `expires_at`.
    - Automatically marks the session as `is_revoked = True` in the database when a timeout is triggered.
    - Rejects requests with a clear, distinct `401 Unauthorized` with detail `"SESSION_EXPIRED"`.
    - Automatically updates `last_active_at` on every successful authenticated request.
  - Created a `clean_expired_sessions` background cleanup helper in [backend/app/services/session_cleanup.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/session_cleanup.py) that revokes any expired or idle sessions.
  - Configured a daily background loop runner inside uvicorn startup lifespan in [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py) to execute this cleanup.
  - Wrote a new automated integration test suite in [backend/tests/test_auto_logout.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_auto_logout.py) that registers, logs in, simulates inactivity by editing database timestamps, verifies rejection with `"SESSION_EXPIRED"`, and verifies database session cleanup.
  - Verified all tests passed successfully with uvicorn server running locally.
- **Files Created:**
  - [backend/app/services/session_cleanup.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/session_cleanup.py)
  - [backend/tests/test_auto_logout.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_auto_logout.py)
- **Files Modified:**
  - [backend/app/core/config.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/config.py)
  - [backend/app/core/security.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/security.py)
  - [backend/app/api/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/auth.py)
  - [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py)
- **Deliverable:** ✅ Authenticated routes monitor idle state, raise custom 401 SESSION_EXPIRED on timeout, update DB timestamps, and execute background sweeps.

---

### Day 11 — Auto-Logout on the Frontend (2026-07-06) ✅
> **Goal:** Reflect session expiry properly in the user interface, and close the loop the user actually experiences.
- **Achievements:**
  - Updated the Zustand global authentication store [useAuthStore.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/store/useAuthStore.ts) to manage both `access_token` and `refresh_token` in sync with client storage, and wired the `logout` action to hit the `/auth/logout` endpoint in the backend to invalidate the database session.
  - Implemented the Axios interceptor in [api.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/services/api.ts) that:
    - Automatically retries failed requests with token expiration by calling `/auth/refresh` to get rotated access and refresh tokens.
    - If the refresh token is expired or the backend returns `SESSION_EXPIRED`, it clears the storage, logs the user out, and redirects to `/login?expired=true`.
  - Created a global [IdleTimer](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/components/IdleTimer.tsx) component in the React app that:
    - Adds window event listeners (`mousemove`, `mousedown`, `keypress`, `scroll`, `click`, `touchstart`) to detect user activity.
    - Tracks idle state, showing a premium dark glassmorphism warning modal with a 2-minute countdown timer at 13 minutes.
    - Click-anywhere or clicking the warning button resets the timer and counts as active.
    - Logs the user out client-side at 15 minutes of inactivity.
  - Rendered `<IdleTimer />` inside `<BrowserRouter>` in [App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx).
  - Wrote premium warning modal CSS rules in [index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css) to support glassmorphism, countdown timers, and warning states.
  - Verified frontend builds successfully with `npm run build` with zero TypeScript compilation errors.
- **Files Created:**
  - [frontend/src/components/IdleTimer.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/components/IdleTimer.tsx)
- **Files Modified:**
  - [frontend/src/store/useAuthStore.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/store/useAuthStore.ts)
  - [frontend/src/services/api.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/services/api.ts)
  - [frontend/src/pages/Login.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Login.tsx)
  - [frontend/src/App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx)
  - [frontend/src/index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css)
- **Deliverable:** ✅ Inactive users are warned at 13 minutes and automatically logged out at 15 minutes. Short-lived access tokens are refreshed transparently behind the scenes. Zero compilation errors.

---

### Day 12 — Email-Based Two-Factor Authentication: Backend Setup (2026-07-06) ✅
> **Goal:** Establish the database schema, ORM models, validation schemas, and service functions for email OTP codes.
- **Achievements:**
  - Added the `is_2fa_enabled` column to the `users` table via SQLAlchemy mapping and a safe Alembic migration (`931fe5f881a6_migrate_phone_to_email_2fa.py`) that handles existing users without violating constraints.
  - Implemented the database model [EmailOTPVerification](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/email_otp.py) inside `backend/app/models/email_otp.py` to store OTP hashes, attempts, and expiration details.
  - Implemented [otp_service.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/otp_service.py) to generate secure 6-digit random codes, hash them using SHA-256 for secure storage, and handle attempts, expirations, and simulated email delivery.
  - Created API endpoints in [auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/auth.py):
    - `POST /auth/2fa/enable` for triggering an OTP to be sent to the user's registered email address.
    - `POST /auth/2fa/confirm` to verify the code and enable 2FA on the user's account.
    - `POST /auth/2fa/disable` to deactivate 2FA.
  - Exposed `is_2fa_enabled` in `UserResponse` Pydantic model inside [auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/auth.py).
  - Wrote and executed integration tests confirming database storage, formats, and enable/confirm API operations work correctly under test settings. All tests passed.
- **Files Created:**
  - [backend/app/models/email_otp.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/email_otp.py)
  - [backend/app/services/otp_service.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/otp_service.py)
- **Files Modified:**
  - [backend/app/models/user.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/user.py)
  - [backend/app/models/__init__.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/__init__.py)
  - [backend/app/schemas/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/auth.py)
  - [backend/app/api/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/auth.py)
- **Deliverable:** ✅ Backend API endpoints support triggering and confirming Email 2FA. All validation, hashing, attempts tracking, and schemas are fully verified and passing integration tests.

---

### Security Audit & Code Hardening (2026-07-06) ✅
> **Goal:** Audit the frontend/backend codebase for security vulnerabilities, information disclosure, logic leaks, and alignment with project constraints.
- **Achievements:**
  - Audited full backend authentication module, token decoding, validation logic, database session state handling, and Pydantic validation rules.
  - Fixed a **High Severity Information Leak** in `otp_service.py` where plaintext OTP codes were printed to standard server logs/stdout in the production SMS provider path.
  - Gated the `/api/test-llm` debugging endpoint to only compile/run in development environment, returning 404 in production, preventing unauthorized Gemini API billing abuse.
  - Corrected `.env` to enforce the requested `ACCESS_TOKEN_EXPIRE_MINUTES=40` which was previously set to `30` (silently overriding `config.py` defaults).
  - Modified `send_otp()` signature to return `None` instead of returning the plaintext OTP code to callers, eliminating potential downstream leaks.
  - Compiled and executed all backend test suites (`test_phone_otp_schema.py` and `test_phone_2fa_api.py`) verifying post-audit backend logic works cleanly.
- **Files Modified:**
  - [backend/app/services/otp_service.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/otp_service.py)
  - [backend/app/main.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/main.py)
  - [.env](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.env)
- **Deliverable:** ✅ Code hardened against log-based credential leaks, test API endpoints secured, config variables corrected to 40-minute expirations.

---

### Day 13 — Email OTP: Login Flow Integration (2026-07-09) ✅
> **Goal:** Require the email code at login for any user who has 2FA enabled, keeping the flow secure and passwordless after credentials verification.
- **Achievements:**
  - Updated `POST /auth/login` flow: if the user has Email 2FA enabled, it automatically triggers OTP sending to their registered email and returns a short-lived `pending_2fa_token` with `requires_2fa: true` and a masked email display message.
  - Implemented `POST /auth/2fa/login-verify` endpoint to accept `pending_2fa_token` and `otp_code`, decode and validate the token, verify the OTP code, and issue real access and refresh tokens.
  - Implemented `POST /auth/2fa/resend-otp` endpoint to resend OTPs for pending 2FA logins, enforcing a 30-second cooldown between requests.
  - Confirmed that each OTP has a 5-minute expiry and is limited to 5 verification attempts before being invalidated.
  - Wrote a new integration test suite `test_phone_2fa_login.py` (which tests email-based 2FA) covering standard login, 2FA login flow redirection, OTP resending, cooldown enforcement, attempt limiting, and successful 2FA login verification.
  - Successfully ran the test suite against the local FastAPI backend server, with all tests passing.
- **Files Created:**
  - [backend/tests/test_phone_2fa_login.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/tests/test_phone_2fa_login.py)
- **Files Modified:**
  - [backend/app/schemas/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/schemas/auth.py)
  - [backend/app/api/auth.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/api/auth.py)
- **Deliverable:** ✅ A user with 2FA enabled receives an email OTP automatically at login and cannot get in with just a password — the system correctly demands the code, with resend and attempt-limiting handled cleanly.

---

### Day 14 — Email OTP: Frontend (2026-07-09) ✅
> **Goal:** Build a 2FA setup and login experience that feels clean, secure, and low-friction.
- **Achievements:**
  - Built the new **Security Settings** page in [Security.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Security.tsx) incorporating:
    - Triggering configuration to enable Email 2FA by sending OTP directly to logged-in user email.
    - An auto-advancing 6-digit OTP entry container with countdown timer tracking OTP expiry (5 minutes).
    - Display of active 2FA status, including their masked registered email address.
    - "Disable 2FA" button to turn off Email 2FA.
    - Integrated with backend endpoints `/auth/2fa/enable`, `/auth/2fa/confirm`, and `/auth/2fa/disable`.
  - Updated the **Login** page flow in [Login.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Login.tsx):
    - Added an intercepting 2FA screen state triggered if the login API returns `requires_2fa: true`.
    - Integrated the auto-advancing 6-digit OTP boxes, countdown timer, and "Resend code" handler with a 30-second cooldown.
  - Added CSS layout and input focus animations for `.otp-container` and `.otp-digit-input` in [index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css).
  - Registered the protected `/security` path in [App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx) and linked to it via the main navbar in [Dashboard.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Dashboard.tsx).
  - Verified that the frontend application builds and compiles successfully with zero TypeScript or syntax errors (`tsc -b && vite build` succeeded).
  - **Conducted Security Audit & Code Hardening**:
    - Identified and removed orphaned legacy files: `phone_validator.py` (validator helper) and `phone_otp.py` (database model).
    - Removed `demo_user_2fa.py` test script from Git repository to protect local logging directories and plaintext credentials from being pushed to remote history.
    - Cleaned up obsolete config parameters `SMS_API_KEY` and `SMS_SENDER_ID` from `config.py` and `.env` template.
    - Guarded backend plaintext OTP console print logging behind `APP_ENV == "development"` environment checks.
    - Cleaned up obsolete mobile-only Web OTP API handlers from `Login.tsx` and `Security.tsx` since SMS-based auto-fill is no longer applicable to email OTP delivery.
- **Files Created:**
  - [frontend/src/pages/Security.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Security.tsx)
- **Files Deleted:**
  - `backend/app/services/phone_validator.py`
  - `backend/app/models/phone_otp.py`
  - `backend/tests/demo_user_2fa.py`
- **Files Modified:**
  - [frontend/src/index.css](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/index.css)
  - [frontend/src/store/useAuthStore.ts](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/store/useAuthStore.ts)
  - [frontend/src/pages/Login.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Login.tsx)
  - [frontend/src/pages/Security.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Security.tsx)
  - [frontend/src/App.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/App.tsx)
  - [frontend/src/pages/Dashboard.tsx](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/frontend/src/pages/Dashboard.tsx)
  - [backend/app/core/config.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/core/config.py)
  - [backend/app/services/otp_service.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/services/otp_service.py)
  - [backend/app/models/__init__.py](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/backend/app/models/__init__.py)
  - [.env](file:///C:/Users/Lenovo/Downloads/Old%20One%20Drive/AI%20Legal%20Document%20Intelligence%20Platform/.env)
- **Deliverable:** ✅ A user can toggle Email 2FA on/off seamlessly. Logging in requires credentials first, then prompts for a verification code delivered via email, which updates states immediately. Stale SMS config variables and dead validator modules are fully purged, and logs are hardened against plaintext OTP exposures.

### Day 15 — Google Sign-In & Active Sessions (2026-07-18) ✅
> **Goal:** Completely integrate "Sign in with Google" button, verification token endpoint, 2FA bypass logic, active device sessions tracking, and single/bulk session revocation.
- **Achievements:**
  - Configured `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables in `.env` and loaded them via Pydantic `Settings`.
  - Installed `google-auth` in the Python virtual environment.
  - Implemented the `POST /auth/google-login` endpoint in `backend/app/api/auth.py` to verify ID Token credentials and automatically register/log in users.
  - Bypassed 2FA OTP prompt completely for Google Sign-In sessions.
  - Loaded the Google Client script in `frontend/index.html` and updated the app title.
  - Created `frontend/.env` to export the public Google Client ID to Vite.
  - Built the programmatic Google button initializers in `Login.tsx` and `Register.tsx` to handle user response and log in.
  - Wrote a self-contained integration test suite in `backend/tests/test_google_auth.py` and verified all endpoints pass successfully.
  - Implemented session monitoring and revocation backend endpoints `GET /auth/sessions` (list active devices), `DELETE /auth/sessions/{session_id}` (revoke specific session), and `DELETE /auth/sessions` (bulk revoke all other sessions) in `backend/app/api/auth.py`.
  - Added new `UserSessionResponse` Pydantic response schema in `backend/app/schemas/auth.py`.
  - Built the active device sessions list view in `Security.tsx` showing browser device-info, IP address, last active times, and dynamic tagging for the active session.
  - Added CSS layout and transition animations for `.sessions-section` and `.session-item` elements in `index.css`.
  - Created a self-contained integration test suite in `backend/tests/test_sessions.py` to verify session listing and revocation states.
- **Files Created:**
  - `backend/tests/test_google_auth.py`
  - `backend/tests/test_sessions.py`
  - `frontend/.env`
- **Files Modified:**
  - `backend/requirements.txt`
  - `backend/app/core/config.py`
  - `backend/app/schemas/auth.py`
  - `backend/app/api/auth.py`
  - `frontend/index.html`
  - `frontend/src/index.css`
  - `frontend/src/pages/Login.tsx`
  - `frontend/src/pages/Register.tsx`
  - `frontend/src/pages/Security.tsx`
  - `.env`
- **Deliverable:** ✅ Day 15 is complete. Users can authenticate with Google (bypassing 2FA), monitor active device sessions, and log out/revoke other active devices from the security dashboard. Phase 2A is 100% complete and fully verified.

---

## ⚙️ Project Environment & Configuration State


### Python Environment
- **Python Version:** CPython 3.11.x (from `C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe`)
- **Virtual Environment:** `backend/venv/` (CPython 3.11, `Scripts/` layout)
- **⚠️ Note:** System `python` command points to MSYS2 (`C:\msys64\ucrt64\bin\python.exe`) — **always use `backend\venv\Scripts\python` explicitly** when running project scripts or tests.

### Backend Config
- **Language/Framework:** FastAPI 0.115.0 / Python 3.11
- **Port:** `8000` ✅ verified
- **Key Dependencies Installed:**
  - fastapi 0.115.0, uvicorn 0.30.6, sqlalchemy 2.0.35, alembic 1.13.2
  - psycopg2-binary 2.9.9, pydantic 2.9.2, pydantic-settings 2.5.2
  - python-jose 3.3.0, passlib 1.7.4, **bcrypt 4.2.1** (pinned — 5.x incompatible with passlib)
  - python-multipart 0.0.12, email-validator 2.3.0
  - **google-generativeai 0.8.6** ✅
- **Environment Variables State (`.env`):**
  - `DATABASE_URL`: `postgresql://postgres:postgres@localhost:5432/legal_ai_db` ✅
  - `JWT_SECRET_KEY`: `cryptographically secure 256-bit key` (set)
  - `JWT_ALGORITHM`: `HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES`: `40`, `REFRESH_TOKEN_EXPIRE_DAYS`: `7` ✅
  - `GEMINI_API_KEY`: Configured and verified working ✅
  - `GEMINI_MODEL`: `gemini-3.5-flash` ✅

### Database Config
- **DBMS:** PostgreSQL 18.4 at `C:\Program Files\PostgreSQL\18\` ✅
- **Database:** `legal_ai_db` ✅ created and migrated
- **Migration Engine:** Alembic 1.13.2 ✅ initialized, migration `589ef280e83a` applied ✅
- **Tables:** `users`, `contracts`, `analyses`, `audit_logs`, `user_sessions`, `alembic_version` ✅

### Frontend Config
- **Framework:** React (Vite) — placeholder only (initialized Day 7)
- **Port:** `5173` (planned)

---

## 📝 Ongoing Notes & Design Decisions

- **Decision 0.1:** Initialized the ledger in `session_state.md` at the project root to ensure continuous, structured tracking of each day's objectives and changes.
- **Decision 2.1:** Used **CPython 3.11** from python.org instead of MSYS2/UCRT64 Python (3.12) because MSYS2 Python doesn't have prebuilt wheels on PyPI, causing compilation failures for pydantic-core, psycopg2-binary, and greenlet.
- **Decision 2.2:** Kept `psycopg2-binary` (psycopg2) instead of `psycopg` (psycopg3) since CPython 3.11 has prebuilt wheels available and psycopg2 is the more battle-tested driver with broader SQLAlchemy documentation coverage.
- **Decision 2.3:** The `.env` file loads from the project root (one level above `backend/`). The `config.py` module uses `pydantic-settings` with `env_file=".env"` which resolves relative to the working directory. The server is started from `backend/` — so the working directory must be `backend/` when running uvicorn.
- **Decision 2.4 (Revised):** Switched the primary LLM from **Zhipu AI GLM-4.7-Flash (Z.AI)** to **Google Gemini 3.5 Flash** (Google AI Studio). Reasons: Z.AI hit rate limits; Gemini free tier has 15 RPM / 1,500 req/day; same key covers embeddings.
- **Decision 2.5:** The `LLMService` class uses a module-level singleton to avoid re-loading credentials on every request.
- **Decision 3.1:** All ORM models use **SQLAlchemy 2.x `mapped_column` / `Mapped[T]`** style rather than the legacy `Column()` API. This provides full type-checker support and is the recommended approach going forward.
- **Decision 3.2:** `AuditLog.user_id` is `nullable=True` with `ON DELETE SET NULL` (not CASCADE) — so deleting a user preserves the audit trail. Audit logs are append-only and must never be dropped with the user.
- **Decision 3.3:** `Analysis.result_json` and `AuditLog.metadata_json` use `JSONB` (PostgreSQL binary JSON) rather than plain `JSON` for indexing capability and faster query performance on JSON fields.
- **Decision 4.1:** Pydantic schemas live in a dedicated `backend/app/schemas/` directory, separate from `models/`, following FastAPI convention. This prevents circular imports when auth.py needs both ORM models and response schemas.
- **Decision 4.2:** `POST /auth/login` returns the same `"Invalid credentials"` error whether the email doesn't exist or the password is wrong. This prevents user enumeration — an attacker cannot distinguish between "email not found" and "wrong password" from the API response.
- **Decision 4.3:** `bcrypt` is pinned to `==4.2.1`. `bcrypt 5.x` introduced a strict 72-byte password limit check that throws a `ValueError` inside `passlib 1.7.4`. Since `passlib` is unmaintained, the safest fix is pinning bcrypt to the last compatible 4.x release.
- **Decision 4.4:** Absolute Path for Env File Loading: Updated `config.py` to use `Path(__file__).resolve().parents[3] / ".env"` rather than a relative path `".env"`. This ensures `.env` loads correctly regardless of the directory from which uvicorn is launched.
- **Decision 8.1:** Server Startup Commands: Documented the local dev server startup commands:
  * Backend API: Run `venv\Scripts\python -m uvicorn app.main:app --port 8000` inside the `backend/` directory.
  * Frontend App: Run `npm run dev` inside the `frontend/` directory (accessible at `http://localhost:5173`).
- **Decision 9.1:** Implemented refresh tokens using cryptographically secure random 64-character hex strings (`secrets.token_hex(32)`) hashed with SHA-256 at rest, rather than encoding user data in a secondary JWT. This keeps refresh tokens simple, completely random, and easily revocable in the database.
- **Decision 9.2:** Implemented refresh token rotation (revoking the old refresh token and generating a new one on every refresh request) to defend against replay attacks and ensure robust session state management.
- **Decision 10.1:** Designed the session activity tracker and idle timeouts to be processed directly inside the `get_current_user` FastAPI dependency. This allows direct, high-performance database access and user verification on authenticated endpoints, avoiding the overhead of separate global middleware processing for public routes (e.g., `/health`, `/auth/login`, `/auth/register`).
- **Decision 10.2:** Implemented a background loop runner directly in the FastAPI lifespan event loop to clean up expired sessions daily. This avoids needing external cron job scheduling configurations on local systems, keeping the container/development setup self-contained.
- **Decision 11.1:** Implemented Axios interceptors to automatically catch 401 token expiry errors and attempt token refresh requests seamlessly in the background. If the session has completely expired (raising `"SESSION_EXPIRED"`), the interceptor prevents infinite retries and redirects the user immediately to `/login?expired=true`.
- **Decision 11.2:** Designed client-side activity tracking using global event listeners on active UI interactions (`mousemove`, `mousedown`, `keypress`, `scroll`, etc.) to reset a local timeout. A custom UI warning modal with a countdown is rendered at 13 minutes, allowing users to extend their session or logging them out securely at 15 minutes.
- **Decision 12.1:** Transitioned from phone-based 2FA validation to email-based 2FA verification. Dropped all phone-specific regex validators and database columns to streamline the verification flow directly using the user's primary registered email address.
- **Decision 12.2:** Stored OTP codes securely in the database as SHA-256 hashes (`otp_hash`) rather than plaintext. Expiration checks (5 minutes) and attempt tracking (max 5) are managed directly on the DB record state, locking the verification when exceeded.
- **Decision S.1:** Modified the OTP service to omit plaintext OTP codes from production-level logs and error traces, keeping them solely in the simulated local mock environment to prevent credentials leakage.
- **Decision S.2:** Gated developer test endpoints like `/api/test-llm` behind environment checks (`APP_ENV == "development"`) to prevent unauthenticated access and potential API token abuse/cost generation in production environments.
- **Decision 13.1:** Encoded the user email and the pending state (`"pending_2fa": True`) into a short-lived pending 2FA JWT token (5-minute expiry) to securely transfer login state between `/auth/login` and `/auth/2fa/login-verify` without storing the password or state in plain text. Since this pending token lacks the required `session_id` claim, it is automatically rejected by the `get_current_user` dependency, ensuring it cannot be misused for authenticated API requests.
- **Decision 13.2:** Implemented a 30-second cooldown on `/auth/2fa/resend-otp` by checking the `created_at` timestamp of the matching `EmailOTPVerification` row, raising `429 Too Many Requests` if the limit is violated to prevent gateway spam and abuse.
- **Decision 14.1:** Designed the Security Settings page with a toggle split UI: a status card showing active 2FA details, and a dynamic activation trigger that generates and dispatches a code directly to the active logged-in email without requiring any manual text entry.
- **Decision 14.2:** Integrated the auto-advancing 6-digit OTP verification panel using an array state ref pattern for focusing next/previous input elements on digit key events, ensuring low friction code submissions.
- **Decision 14.3:** Aligned Zustand auth store interfaces to match database user attributes (`is_2fa_enabled`), triggering state updates immediately on successful 2FA activations/deactivations so the UI transitions state seamlessly without requiring full page refreshes.
