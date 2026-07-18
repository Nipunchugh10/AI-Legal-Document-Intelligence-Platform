**NOTE : THIS FILE WILL ALWAYS REMAIN IN gitignore, never push it on the github repository**
**NOTE : ALWAYS REMEBER THAT YOU ARE WORKING ON AN APPLICATION THAT IS SUPPOSED TO BE ABLE TO WORK PROPERLLY ON PRODUCTION SCALE AND CAN HANDLE LARGE NUMBER OF USERS SMOOTHLY, THE DATA PROTECTION MUST BE ROBUST AND CODE SHOULD BE OPTIMIZED**

# AI Legal Document Intelligence Platform
## Project Proposal and 62-Day Day-by-Day Build Plan

---

## Part 1 — The Problem, The Solution, and Why This Matters

*(Written for anyone, technical or not, to understand what this project does and why it deserves trust.)*

---

### The Problem

Every day, ordinary people sign documents they do not fully understand.

A freelancer signs a client contract without realizing it gives away rights to all their future work, not just the project at hand. A small business owner signs a rental agreement without noticing a clause that lets the landlord raise rent without notice. A new employee signs an offer letter without realizing there is no cap on how much they could be held financially liable for if something goes wrong.

This happens because legal documents are written in dense, technical language. Hiring a lawyer to review every contract is expensive and slow. Most people are left with two bad choices: sign blindly and hope for the best, or spend money and time they don't have getting professional advice for something that might take a lawyer ten minutes to explain.

**The real cost of this problem is invisible until it's too late** — a lost dispute, an unexpected penalty, a clause that was always there but nobody read carefully.

---

### The Solution

This platform acts like a careful, knowledgeable friend who reads the fine print for you.

A person uploads any contract, NDA, rental agreement, or service agreement as a PDF. Within about a minute, the platform:

1. **Explains what the document actually is** — who the parties are, what it covers, and in plain English, what it means
2. **Finds the important clauses** — payment terms, termination conditions, liability, confidentiality — and pulls them out so nothing important is buried in pages of text
3. **Flags the risky parts** — clauses that are one-sided, have no caps on penalties, or quietly favor the other party — and explains exactly why each one is a concern
4. **Checks it against standard legal practice** — comparing the document to known fair-contract norms, so missing protections or unusual terms stand out
5. **Lets the person ask questions in plain language** — like talking to an assistant — for example, "Can I get out of this contract early?" — and get an answer that points to the exact clause it came from, rather than a generic guess

On top of this, the platform remembers everything: every document a person has uploaded, every question they've asked, every analysis it has run — all organized and searchable, the same way a well-organized lawyer's filing cabinet would work, except instant and digital.

---

### What Benefits Does This Bring

**For the person using it:**
- Understands what they are agreeing to before they sign, not after something goes wrong
- Saves the cost and delay of getting a lawyer involved for routine document reviews
- Builds a permanent, searchable record of every contract they have ever signed, so months or years later they can instantly find "which contract had that indemnity clause" instead of digging through email attachments
- Gets specific, usable suggestions for negotiating better terms, not just a list of problems

**For a business:**
- Standardizes how contracts are reviewed across the company, so quality doesn't depend on which employee happened to read it
- Creates a complete audit trail of who looked at which document and when, which matters for compliance and accountability
- Catches risky clauses before they become expensive problems

---

### Why Should Anybody Trust This Application

Trust is the entire foundation of a platform that handles people's contracts, financial agreements, and private legal matters. If a person cannot trust that their data is safe, the product has no value no matter how good the analysis is. This is why this plan treats trust and security as a first-class feature, not an afterthought added at the end.

Specifically, this platform is being built so that:

1. **Only the real account owner can get in.** Beyond a password, the platform will require a second proof of identity (Two-Factor Authentication) using a one-time code sent directly to the user's phone via SMS — the same experience as logging into a bank app or completing an online payment. There is no app to download or QR code to scan; the user simply receives a 6-digit code by text message and enters it. Even if someone steals a password, they cannot get into the account without also having physical access to the user's phone. At launch, this feature is built specifically for Indian phone numbers, so the platform can guarantee fast, reliable SMS delivery and keep costs predictable, rather than spreading thin across international carriers from day one.

2. **Sessions don't stay open forever.** If someone closes their laptop or walks away without logging out, the platform automatically logs them out after a period of inactivity — exactly like how a banking website does. This prevents someone else from picking up an unattended device and reading another person's private contracts.

3. **Every action is recorded.** Every login, every document upload, every question asked, every analysis run is logged with a timestamp. If anything unusual happens, there is a complete, honest record of exactly what occurred and when — nothing is hidden or silently lost.

4. **A person's documents belong only to them.** The system is built so that one user's contracts, conversations, and history can never be accessed by another user, enforced at every layer of the application, not just hidden in the interface.

5. **Nothing is a black box.** The platform explains its reasoning — every risk it flags points to the specific clause that caused the concern, and every Q&A answer cites where in the document it came from. The person is never asked to "just trust the AI" without evidence.

In short: the analysis is only as valuable as the trust behind it, and this plan is built so that the security and privacy work is done properly, not bolted on at the end.

**A note on scope:** At launch, the phone-verification step described above only works with Indian mobile numbers. This is a deliberate first-version decision, not a limitation discovered later — it lets the platform guarantee that every OTP message is delivered quickly and reliably through properly registered, compliant SMS routes within India, rather than offering a shaky experience across many countries at once. Supporting other countries can be added later once the core product is proven.

---

### Why This Is Different From Just Using ChatGPT or Gemini Directly

A fair question anyone will ask is: general AI assistants like ChatGPT and Gemini are extremely capable — so why build a separate platform instead of just pasting a contract into one of them? The honest answer is that this platform is not claiming to have a smarter AI underneath. It is built on similar underlying language models. What it offers instead is **engineering and workflow built specifically around legal documents**, which a general-purpose chat assistant does not provide out of the box. Five things make this platform meaningfully different, and each one is deliberately built into this plan rather than left as an afterthought:

| # | Differentiator | Why a general chatbot doesn't do this | Where it is built in this plan |
|---|---|---|---|
| 1 | **Grounded, cited answers** — every answer points to the exact clause it came from, not a best-effort guess | ChatGPT/Gemini only know what's in the current chat window; there's no structured retrieval against a specific document, and no built-in citation back to source text | Vector DB and embedding pipeline (Days 18–19), Q&A Agent with mandatory source citation (Day 26), conversation messages store `cited_clause_refs` for every answer (Days 45–46) |
| 2 | **A repeatable, structured analysis pipeline** — every document goes through the same five-step process, not a single freeform answer | A general chatbot gives you whatever depth of analysis you happen to prompt for, which varies by how well the question is worded | The five-agent LangGraph workflow: Parsing → Clause Detection → Risk Assessment → Compliance → Q&A (Days 20–27), orchestrated as one fixed pipeline (Day 27) |
| 3 | **Persistent, organized, searchable history** — every contract and every conversation is saved and findable later | ChatGPT conversations get buried in general chat history with no document-specific organization or semantic search across past uploads | Semantic search across all contracts (Days 40–41), full conversation persistence and resumable Q&A threads (Days 45–47), activity timeline (Day 47) |
| 4 | **Security built for sensitive legal and financial documents** — phone-based 2FA, auto-logout, full audit trail | General AI chat tools are not built around protecting a person's private contracts specifically, and most don't offer a dedicated audit trail of who accessed what and when | Entire Phase 2A — sessions, auto-logout, phone OTP 2FA (Days 8–15); audit logging and data isolation (Days 45–46, 48); security hardening pass (Day 60) |
| 5 | **Consistent quality regardless of how the question is phrased** — the same rigorous checklist runs on every document, every time | A chatbot's depth and accuracy can shift noticeably depending on prompt wording, with no guarantee the same checks are run twice in a row | Fixed clause/risk/compliance checklist applied identically by every agent (Days 22–25); dedicated cross-document consistency testing pass, not just isolated prompt fixing (Days 57–58) |

This table is meant to be the answer, in writing, to "why not just use ChatGPT" — every claim made out loud should be traceable to a specific, buildable piece of the plan below, not just a talking point.

---

## Part 2 — Implementation Plan

This plan is organized into 8 phases across 62 days. Two major capabilities have been added to the original scope and are called out clearly below:

- **Phase 2A — Identity, Sessions, and Phone-Based Two-Factor Authentication (Days 8–15)**: a dedicated phase, inserted right after the basic login system is built, because every other feature in this platform — documents, conversations, history — depends on knowing with certainty who is accessing them. The second factor is delivered as an SMS OTP to the user's registered phone number, chosen specifically because it requires no app download, no setup friction, and is a flow almost every user already understands from banking and e-commerce logins. **At launch, this platform supports Indian phone numbers only (+91)** — this is a deliberate scope decision, not an oversight, and is enforced at every layer: input validation, backend verification, and SMS delivery routing.
- **Phase 6 — Activity History and Conversation Architecture (Days 45–48)**: expanded from a single "audit log" task into a complete subsystem that records, stores, and presents the full history of everything a user has done on the platform, including their document conversations.

---

## Phase 1 — Foundation and Project Setup (Days 1–7)

---

### Day 1 — Project Architecture and Repository Setup

**Goal:** Understand the full system before writing a single line of code.

- Draw the complete system architecture on paper or in a tool like Excalidraw
- Identify all services: FastAPI backend, React frontend, PostgreSQL, Vector DB, LangGraph agents, Session/Auth service, History/Audit service
- Create a GitHub repository with this folder structure:

```
legal-ai-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── models/
│   │   ├── services/
│   │   └── core/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── docker-compose.yml
└── README.md
```

- Create `.env.example` with all environment variables you will need (API keys, DB URLs, etc.)

**Deliverable:** Clean repo with folder structure committed to GitHub.

---

### Day 2 — Backend Project Initialization

**Goal:** Get a working FastAPI project running locally.

> **Hardware note:** All AI inference for this project runs on a free cloud API (Google Gemini 3.5 Flash via Google AI Studio, set up on Day 20), not on your laptop, so no local GPU or large RAM allocation for model weights is needed. The only things running locally are FastAPI, PostgreSQL, and the React dev server — all lightweight enough for an 8GB RAM machine like the one used for this build, as long as Docker Desktop isn't also running Postgres, pgAdmin, the backend, and the frontend all at once during heavy development; close unused containers when not actively testing the full stack together.

- Set up a Python virtual environment
- Install core dependencies:

```
fastapi
uvicorn[standard]
sqlalchemy
alembic
pydantic
pydantic-settings
python-dotenv
psycopg2-binary
python-jose[cryptography]
passlib[bcrypt]
python-multipart
```

- Create `main.py` with a health check endpoint: `GET /health`
- Set up `core/config.py` using `pydantic-settings` to load environment variables
- Set up `core/database.py` with SQLAlchemy engine and session factory
- Run the server and confirm it works at `localhost:8000`

**Deliverable:** FastAPI running with `/health` returning `{"status": "ok"}`.

---

### Day 3 — Database Design and Migrations ✅ *(Completed — 2026-06-22)*

**Goal:** Design and create all database tables, including tables needed for sessions and history.

**Pre-requisite:** Install PostgreSQL locally (if not already). Create the database:
```bash
psql -U postgres -c "CREATE DATABASE legal_ai_db;"
```

**Step 1 — Initialize Alembic:**
```bash
cd backend
venv\Scripts\alembic init alembic
```

**Step 2 — Configure Alembic** (`alembic/env.py`):
- Import `Base` from `app.core.database` and set `target_metadata = Base.metadata`
- Load `DATABASE_URL` from `app.core.config.get_settings()` so migrations read from `.env`

**Step 3 — Create SQLAlchemy models in `backend/app/models/`:**

```
users       → id (PK), email (unique, indexed), hashed_password, is_active (default True), created_at
contracts   → id (PK), user_id (FK→users), filename, upload_path, status (default "pending"), created_at
analyses    → id (PK), contract_id (FK→contracts), analysis_type, result_json (JSON), created_at
audit_logs  → id (PK), user_id (FK→users, nullable), action, resource_id (nullable), metadata_json (JSON), timestamp
```

**Step 4 — Stub comments for future tables** (in `models/__init__.py`):
```
user_sessions            → built Day 11  (Phase 2A)
phone_otp_verifications  → built Day 12–13 (Phase 2A)
conversations            → built Day 46  (Phase 6)
conversation_messages    → built Day 46  (Phase 6)
```

**Step 5 — Run Alembic migration:**
```bash
venv\Scripts\alembic revision --autogenerate -m "initial_schema"
venv\Scripts\alembic upgrade head
```

**Step 6 — Verify** using `psql` or DBeaver:
```sql
\dt          -- should list: users, contracts, analyses, audit_logs, alembic_version
\d users
\d contracts
```

**Step 7 — Commit:**
```bash
git add . && git commit -m "Day 3: Alembic setup and initial DB schema (4 core tables)"
```

**Files Created:**
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/<hash>_initial_schema.py`
- `backend/app/models/user.py`, `contract.py`, `analysis.py`, `audit_log.py`
- `backend/app/models/__init__.py` (updated from stub)

**Deliverable:** PostgreSQL database `legal_ai_db` with 4 core tables created and Alembic tracking enabled. Schema plan for Phase 2A/6 tables documented.

---

### Day 4 — Basic Authentication System ✅ *(Completed — 2026-06-22)*

**Goal:** Build the first version of JWT-based login. (This will be upgraded with sessions and 2FA in Phase 2A.)

**Pre-requisite:** Day 3 complete — `users` table must exist in `legal_ai_db`.

**Step 1 — Complete `core/security.py`** (extends the Day 2 stub):
- `create_access_token(data: dict, expires_delta: timedelta | None = None) -> str`
  - Signs JWT with `HS256` using `JWT_SECRET_KEY`; default expiry 30 minutes
- `decode_access_token(token: str) -> dict | None`
  - Decodes and validates JWT; returns `None` on expiry or bad signature
- `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`
  - FastAPI dependency: extracts Bearer token → decodes → fetches user from DB
  - Raises `HTTPException(401)` if token is missing, expired, or user not found

**Step 2 — Create Pydantic schemas in `backend/app/schemas/auth.py`:**
```
RegisterRequest  → email: EmailStr, password: str (min_length=8)
LoginRequest     → email: EmailStr, password: str
TokenResponse    → access_token: str, token_type: str
UserResponse     → id: int, email: str, is_active: bool, created_at: datetime
```

**Step 3 — Create `backend/app/api/auth.py`** with three endpoints:
- `POST /auth/register` — validates email uniqueness, hashes password, inserts user, returns `UserResponse`
- `POST /auth/login` — verifies email + password, returns `TokenResponse`
- `GET /auth/me` — protected with `Depends(get_current_user)`, returns `UserResponse`

**Step 4 — Register router in `main.py`:**
```python
from app.api import auth
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
```

**Step 5 — Test all endpoints** (Postman or curl):
- `POST /auth/register` → 200, user created
- `POST /auth/register` same email again → 400 `Email already registered`
- `POST /auth/login` valid creds → JWT token returned
- `POST /auth/login` wrong password → 401 `Invalid credentials`
- `GET /auth/me` with valid `Authorization: Bearer <token>` → user info
- `GET /auth/me` with no token → 401
- `GET /auth/me` with expired/invalid token → 401

**Step 6 — Commit:**
```bash
git add . && git commit -m "Day 4: JWT auth — register, login, /me endpoint with get_current_user"
```

**Files Created:** `backend/app/schemas/__init__.py`, `backend/app/schemas/auth.py`, `backend/app/api/auth.py`

**Files Modified:** `backend/app/core/security.py` (add JWT functions + dependency), `backend/app/main.py` (register router)

**Deliverable:** Working basic auth system. `POST /auth/register` creates a user. `POST /auth/login` returns a signed JWT. `GET /auth/me` returns current user when token is valid and rejects tokenless requests with `401`.

> **Note:** This is intentionally a simple, single-token system. Refresh tokens, server-side session storage, auto-logout, and Phone OTP 2FA are all built in Phase 2A (Days 8–15).

---

### Day 5 — File Upload System ✅ *(Completed — 2026-06-28)*

**Goal:** Accept PDF uploads and store them.

- Set up local file storage under `uploads/` directory (simulate S3 for now)
- Create `api/contracts.py` with:
  - `POST /contracts/upload` — accept PDF, save to disk, create DB record, return contract ID
  - `GET /contracts/` — list all contracts for current user
  - `GET /contracts/{contract_id}` — get single contract details
- Validate file type (only PDF allowed)
- Validate file size (max 10MB)
- Write the file path and metadata to the `contracts` table

**Deliverable:** Upload a PDF via Postman, see it saved to disk and recorded in DB.

---

### Day 6 — Docker Setup ✅ *(Completed — 2026-06-28)*

**Goal:** Containerize the entire backend stack.

- Write `Dockerfile` for the FastAPI backend
- Write `docker-compose.yml` with three services:
  - `backend` (FastAPI)
  - `postgres` (PostgreSQL 15)
  - `pgadmin` (optional, for DB browsing)
- Add environment variable passing from `.env` file
- Test: run `docker-compose up` and confirm the API works inside Docker
- Test: confirm the API can connect to PostgreSQL inside Docker

**Deliverable:** `docker-compose up` brings up a fully working backend stack.

---

### Day 7 — Frontend Project Initialization ✅ *(Completed — 2026-06-28)*

**Goal:** Get a React frontend running and connected to the backend.

- Initialize a React + TypeScript project using Vite:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- Install these packages:

```
axios
react-router-dom
@tanstack/react-query
zustand
react-hook-form
tailwindcss
```

- Set up Tailwind CSS
- Create the basic page structure:
  - `/login` — Login page
  - `/register` — Register page
  - `/dashboard` — Protected dashboard
- Set up Axios instance with base URL and JWT token interceptor
- Connect the login form to `POST /auth/login`

**Deliverable:** Login form works. Token is stored. User is redirected to `/dashboard`.

---

## Phase 2A — Identity, Sessions, and Two-Factor Authentication (Days 8–15)

**Why this phase exists:** Everything this platform does — storing contracts, holding private conversations, building a history of a person's legal documents — only matters if the platform can guarantee that the person accessing it is really who they say they are, and that an account left open on a shared or unattended device cannot be misused. This phase is inserted here, right after the basic upload pipeline works, and before any AI agent work begins, because identity is the foundation everything else sits on.

---

### Day 8 — Session Architecture Design ✅ *(Completed — 2026-06-28)*

**Goal:** Design how sessions, expiry, and multi-device login will work before writing code.

- Decide on the session model: short-lived JWT access tokens (15 minutes) + long-lived refresh tokens (7 days), stored server-side so they can be revoked
- Design the `user_sessions` table:

```
user_sessions
  id
  user_id
  refresh_token_hash
  device_info        (browser/OS string)
  ip_address
  created_at
  last_active_at
  expires_at
  is_revoked
```

- Decide the auto-logout policy:
  - **Idle timeout:** 15 minutes of no activity on the frontend logs the user out automatically
  - **Absolute session limit:** even with activity, a session fully expires after 7 days and requires login again
- Document this design in `ARCHITECTURE.md` under a new "Security and Sessions" section

**Deliverable:** A written, reviewed design for how login sessions, expiry, and auto-logout will work.

---

### Day 9 — Refresh Token Backend Implementation ✅ *(Completed — 2026-07-06)*

**Goal:** Replace the simple JWT-only login with a proper access + refresh token system.

- Create the `user_sessions` table via Alembic migration ✅
- Update `core/security.py`: ✅
  - `create_access_token()` — short-lived (15 min)
  - `create_refresh_token()` — long-lived (7 days), stored hashed in `user_sessions`
- Update `POST /auth/login` to issue both tokens and create a session record ✅
- Add `POST /auth/refresh` — exchanges a valid refresh token for a new access token (with rotation) ✅
- Add `POST /auth/logout` — revokes the current session's refresh token ✅

**Deliverable:** Login returns both tokens. Calling `/auth/refresh` issues a new access token without re-entering a password. All integration tests passed successfully.

---

### Day 10 — Auto-Logout on Inactivity (Backend Support) ✅ *(Completed — 2026-07-06)*

**Goal:** Make the backend aware of session activity so idle sessions can be expired.

- On every authenticated request, update `last_active_at` on the matching session record ✅
- Add a check in `get_current_user`: if `last_active_at` is older than the idle timeout (15 minutes), reject the request with a clear `401 SESSION_EXPIRED` error code ✅
- Add a scheduled cleanup job (run via background loop task in lifespan event) that marks expired sessions as `is_revoked = true` daily ✅

**Deliverable:** A session that has been idle for more than 15 minutes is automatically rejected with a clear "session expired" response. All integration tests passed successfully.

---

### Day 11 — Auto-Logout on the Frontend ✅ *(Completed — 2026-07-06)*

**Goal:** Reflect session expiry properly in the user interface, and close the loop the user actually experiences.

- Add an Axios response interceptor: if the API returns `SESSION_EXPIRED` or `401`, automatically log the user out and redirect to `/login` with a message: "You were logged out due to inactivity." ✅
- Add a frontend idle timer (using a library like `idle-timer` or a simple custom hook) that: ✅
  - Tracks mouse movement, clicks, and keystrokes
  - Shows a warning modal at 13 minutes: "You'll be logged out in 2 minutes due to inactivity — click anywhere to stay logged in"
  - Logs the user out client-side at 15 minutes if no activity occurs

**Deliverable:** Leave the app idle for 15 minutes — the user is automatically logged out and shown a clear explanation why. The build passed successfully with zero TypeScript compilation errors.

---

### Day 12 — Email-Based Two-Factor Authentication: Backend Setup ✅ *(Completed — 2026-07-06)*

**Goal:** Add a second layer of identity verification using a one-time code (OTP) sent to the user's registered email address.

- Add an `is_2fa_enabled` boolean field to the `users` table via Alembic migration, indicating whether 2FA is active. ✅
- Create the `email_otp_verifications` table tracking attempts, expiry, and hashes. ✅
- Create `services/otp_service.py` to generate 6-digit random codes, hash them, send (via Email / console mock), and verify. ✅
- Add endpoints: ✅
  - `POST /auth/2fa/enable` — triggers sending an OTP to the authenticated user's email address to start setup.
  - `POST /auth/2fa/confirm` — verifies the OTP and sets `is_2fa_enabled = True` on the user account.
  - `POST /auth/2fa/disable` — disables 2FA for the account.

**Deliverable:** A user can initiate Email 2FA, receive an email with a 6-digit code (mocked in console for dev), and confirm it to activate 2FA. All integration tests pass.

---

### Day 13 — Email OTP: Login Flow Integration ✅ *(Completed — 2026-07-09)*

**Goal:** Require the email code at login for any user who has 2FA enabled, keeping the flow secure and passwordless after credentials verification.

- Update `POST /auth/login` flow:
  1. Verify email + password as before.
  2. If the user has 2FA enabled, do **not** issue tokens yet — automatically trigger `send_otp()` to their registered email address, and return a short-lived `pending_2fa_token` with `requires_2fa: true` and the email address masked for display (e.g., "Code sent to n••••3@gmail.com").
  3. Add `POST /auth/2fa/login-verify` — accepts the `pending_2fa_token` plus the 6-digit code, and only then issues the real access + refresh tokens.
- Add `POST /auth/2fa/resend-otp` — lets the user request a new code, with a 30-second cooldown between requests to prevent spam.
- Limit each OTP to 5 verification attempts before it is invalidated, tracked via `attempts` on the `email_otp_verifications` table.
- Keep the OTP short-lived (5 minutes) so codes can't be reused or guessed.

**Deliverable:** A user with 2FA enabled receives an email OTP automatically at login and cannot get in with just a password — the system correctly demands the code, with resend and attempt-limiting handled cleanly.

---

### Day 14 — Email OTP: Frontend ✅ *(Completed — 2026-07-09)*

**Goal:** Build a 2FA setup and login experience that feels clean, secure, and low-friction.

- Build a **Security Settings** page with an "Email Two-Factor Authentication" section:
  - If 2FA is disabled: show an "Enable Email 2FA" button. On click, it triggers `/auth/2fa/enable` and immediately renders a 6-digit code entry screen with a countdown timer.
  - If 2FA is enabled: show a green success card ("Two-Factor Authentication is Active") displaying the masked email address, and provide a "Disable 2FA" button calling `/auth/2fa/disable`.
- Update the Login page flow:
  - After email/password, if `requires_2fa` is returned, show a single clean screen: "Enter the code sent to your email n••••3@gmail.com", a 6-digit input (auto-advancing between digit boxes), and a "Resend code" link that activates after 30 seconds.
  - Keep this screen to one explicit action — entering the code — with no additional choices.
- Add plain-English explanations near the setup toggle describing the security benefits of 2FA.

**Deliverable:** A user can toggle Email 2FA on/off seamlessly. Logging in requires credentials first, then prompts for a verification code delivered via email, which updates states immediately.

---

### Day 15 — Session Management UI, Google Sign-In, and Security Review

**Goal:** Give users visibility and control over their own sessions, integrate Google Sign-In with 2FA bypass logic, and review the whole phase for gaps.

- Build a **"Active Sessions"** view in Security Settings, listing:
  - Device/browser, approximate location (from IP), last active time, and a "This device" tag for the current session
  - A "Log out" button per session, and a "Log out of all other devices" button
- Wire this to `GET /auth/sessions` and `DELETE /auth/sessions/{session_id}`
- **Google Sign-In Integration** ✅ *(Completed — 2026-07-18)*:
  - Load the Google Identity Services SDK on the frontend (`https://accounts.google.com/gsi/client`).
  - Render the Google Login button on `/login` and `/register` pages.
  - Implement the `POST /auth/google-login` endpoint on the backend.
  - Verify the Google ID token (`credential`) server-side using the `google-auth` Python library.
  - If the user is new (email not in DB), automatically register them with a random hashed password. If the user already exists, retrieve their record.
  - **Exempt Google users from 2FA OTP verification**: Google-authenticated logins directly issue access and refresh tokens without requesting or verifying a phone number OTP, bypassing the 2FA flow entirely. Only standard email/password logins require the SMS OTP step.
- **SMTP Real Email Delivery Preparation**:
  - Add standard SMTP configuration variables to `.env.example` and config schema:
    - `SMTP_HOST`: SMTP server host (e.g., `smtp.gmail.com`, `smtp.sendgrid.net`, `smtp.mailgun.org`)
    - `SMTP_PORT`: Port (typically `587` for TLS or `465` for SSL)
    - `SMTP_USERNAME`: Login email or API username
    - `SMTP_PASSWORD`: Secure app password or API token
    - `SMTP_FROM_EMAIL`: Sender address display (e.g., `no-reply@legalintelligence.com`)
  - Outline the Python `smtplib` and `email.mime` implementation plan inside `otp_service.py` to establish secure TLS connections and deliver the 6-digit verification code to user inboxes.
- Run a full manual security review of Phase 2A:
  - Confirm passwords and third-party tokens are never logged in plaintext
  - Confirm OTP codes are hashed at rest and never written to application logs in plain text
  - Confirm a revoked session truly cannot be used again (test by capturing a token and revoking it, then retrying the request)
  - Confirm OTP attempt limits and resend cooldowns actually block brute-force guessing in practice, not just in theory
  - Confirm non-Indian phone numbers are rejected consistently for standard credentials users — test this explicitly with a handful of malformed and international numbers
  - Confirm rate limiting will later be added to all login, refresh, and OTP endpoints (formally hardened on Day 54)

**Deliverable:** Users can manage active sessions, log in or register passwordlessly via Google with 2FA bypassed, and change their registered phone number securely. Phase 2A is reviewed end-to-end and confirmed working before moving on to document intelligence features.

---

## Phase 2B — Document Parsing Agent (Days 16–22)

*(This is the original Phase 2, renumbered to follow the new security phase.)*

---

### Day 16 — PDF Text Extraction (Completed)

**Goal:** Extract raw text from uploaded PDFs.

- Install:

```
pymupdf
pdfplumber
```

- Create `services/pdf_extractor.py`
- Implement two extraction strategies:
  - `extract_with_pymupdf(filepath)` — fast, good for text-based PDFs
  - `extract_with_pdfplumber(filepath)` — better for tables and multi-column layouts
- Write logic to detect if PDF is text-based or scanned
- Store the extracted text in the `analyses` table with `analysis_type = "raw_text"`
- Add a `POST /contracts/{contract_id}/extract` endpoint that triggers extraction

**Deliverable:** Upload a contract PDF, call the endpoint, get the extracted text back.

---

### Day 17 — Document Chunking and Preprocessing

**Goal:** Prepare text for embedding and agent processing.

- Install:

```
langchain-text-splitters
tiktoken
```

- Create `services/chunker.py`
- Implement `RecursiveCharacterTextSplitter` with:
  - `chunk_size = 1000` tokens
  - `chunk_overlap = 200` tokens
- Preprocess the text before chunking:
  - Remove excessive whitespace
  - Normalize line breaks
  - Remove page headers/footers (page numbers, etc.)
- Store chunks in the `analyses` table with `analysis_type = "chunks"`
- Test with at least three different PDF types (NDA, service agreement, rental contract)

**Deliverable:** Any uploaded PDF gets split into clean, overlapping chunks.

---

### Day 18 — Vector Database Setup and Free Embedding Model

**Goal:** Set up Supabase Vector or Pinecone for storing embeddings, using a free Chinese embedding model instead of a paid Western one.

> **Budget and model-choice note:** This plan does not use the OpenAI API anywhere, since it requires a paid account. Instead, the chat/agent reasoning layer runs on **Google Gemini 3.5 Flash** via Google AI Studio — a genuinely free tier (15 RPM, 1,500 requests/day, 1M tokens/min) with no credit card required. **Embeddings** use Google's **Gemini Embedding** model (`gemini-embedding-001`), also available on the same free API key. See the new **"Free AI Stack Setup"** section on Day 20 for the full reasoning and setup steps.

- Choose one:
  - **Option A: Supabase Vector** — enable pgvector extension, use existing PostgreSQL (recommended, since it's also free and avoids managing a second cloud account)
  - **Option B: Pinecone** — create an account, get API key (also has a free tier)

- If using Supabase Vector, note the embedding dimension: Google's Gemini Embedding model (`gemini-embedding-001`) produces **768-dimension** vectors by default — use **768** for this project, which gives strong retrieval quality while keeping storage and query cost reasonable for a portfolio-scale vector table:

```sql
CREATE EXTENSION vector;
CREATE TABLE contract_embeddings (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES contracts(id),
    chunk_text TEXT,
    embedding VECTOR(768),
    chunk_index INTEGER
);
```

- The same Google AI Studio API key already configured in `.env` covers embeddings too — no additional signup required. The `gemini-embedding-001` model is included in the free tier (15 RPM, 1,500 requests/day).
- Install:

```
google-generativeai>=0.8.0
```

- Create `services/embedder.py` with function `embed_chunks(chunks)` using Google's `models/gemini-embedding-001` model via the `google.generativeai` SDK
- Test embedding a small batch of chunks

**Deliverable:** Function that takes a list of strings and returns a list of 1024-dimension vectors, running on a free Chinese-model token grant.

---

### Day 19 — Embedding Pipeline

**Goal:** Build end-to-end pipeline: PDF → chunks → embeddings → vector DB.

- Create `services/ingestion_pipeline.py`
- Implement the full pipeline:

```python
async def ingest_contract(contract_id: int):
    text = extract_text(contract_id)
    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)
    store_embeddings(contract_id, chunks, embeddings)
    update_contract_status(contract_id, "ingested")
```

- Add a `POST /contracts/{contract_id}/ingest` endpoint
- Handle errors at each step: log failures, update contract status to "failed"
- Test the full pipeline end-to-end

**Deliverable:** Call `/ingest`, PDF goes through the full pipeline, embeddings stored in vector DB.

---

### Day 20 — Free AI Stack Setup, LangGraph Introduction, and Agent Setup

**Goal:** Properly wire up the free LLM provider this entire project will run on, then set up LangGraph and understand the framework before building agents.

**Part A — Free AI Stack Setup**

- The primary LLM for every agent in this project is **Google Gemini 3.5 Flash**, accessed via the Google AI Studio API. The API key (`GEMINI_API_KEY`) is already configured in `.env` from Day 2 and has been end-to-end verified. The free tier provides 15 RPM, 1,500 requests/day, and 1M tokens/min — more than sufficient for the full development and testing phase.
  - Use **`gemini-3.5-flash`** as the default model — it offers superior reasoning compared to older Flash generations, making it ideal for multi-step legal reasoning agents. The model name can be changed in `.env` with a one-line edit, requiring no code changes.
  - The same API key also covers the embedding model (`models/gemini-embedding-001`), used by the vector pipeline — no second account needed.
- **Resilience note:** Free tiers from any single provider can change quota without warning. To avoid the pipeline stalling, configure **Groq** (`console.groq.com`, free, no credit card required) running **Llama 3.3 70B** as an automatic fallback. This is a safety net only — the project's primary AI identity stays on Google Gemini.
- Install:

```
langgraph
langchain
google-generativeai>=0.8.0
langchain-google-genai
langchain-groq
tenacity
```

- Create `services/llm_provider.py` — a small wrapper that calls Gemini 3.5 Flash first and automatically falls back to Groq's Llama 3.3 70B on a rate-limit error:

```python
import google.generativeai as genai
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)
primary_model = genai.GenerativeModel(settings.GEMINI_MODEL)
fallback_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
def get_llm_response(prompt: str, use_fallback: bool = False) -> str:
    if use_fallback:
        return fallback_llm.invoke(prompt).content
    try:
        response = primary_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0)
        )
        return response.text
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return get_llm_response(prompt, use_fallback=True)
        raise
```

- Every agent built from this point forward (Days 21–26) calls `get_llm_response()` rather than hitting a single provider directly, so the fallback is built into the foundation, not bolted on later
- Add both `GEMINI_API_KEY` and `GROQ_API_KEY` to `.env.example`, with a short comment explaining which is primary and which is the safety net

**Part B — LangGraph Introduction**

- Read the LangGraph documentation on:
  - State graphs
  - Nodes and edges
  - State schemas
  - Conditional edges

- Create `agents/base.py` with the shared state schema:

```python
class ContractAnalysisState(TypedDict):
    contract_id: int
    raw_text: str
    chunks: list[str]
    clauses: dict
    risks: list[dict]
    compliance_issues: list[dict]
    summary: str
    messages: list
```

- Build a minimal test graph: `start → extract_text → end`
- Run it and confirm state flows correctly

**Deliverable:** A working `get_llm_response()` function that runs on Gemini 3.5 Flash (free, Google AI Studio) by default and falls back to Groq's Llama 3.3 70B if the Gemini free tier is ever rate-limited, plus a working LangGraph state graph that accepts a contract ID and returns extracted text.

---

### Day 21 — Document Parsing Agent (Agent 1)

**Goal:** Build the first official agent that parses and structures document content.

- Create `agents/parsing_agent.py`
- The parsing agent does two things:
  1. Extracts text from the PDF
  2. Identifies the document type (NDA, Service Agreement, Employment Contract, Rental Agreement, etc.)

- System prompt for document type detection:

```
You are a legal document classifier. Given the following text from a legal document, identify:
1. The document type
2. The parties involved (Party A and Party B)
3. The effective date if mentioned
4. The jurisdiction if mentioned

Return a JSON object with keys: document_type, party_a, party_b, effective_date, jurisdiction.
```

- Integrate this node into the LangGraph workflow
- Test with three different document types

**Deliverable:** Agent correctly identifies document type and extracts parties from a contract.

---

### Day 22 — Clause Detection Agent (Agent 2)

**Goal:** Build the agent that identifies and extracts specific legal clauses.

- Create `agents/clause_agent.py`
- Target these clause types:

```
payment_terms
termination_clauses
liability_clauses
confidentiality_clauses
intellectual_property_clauses
dispute_resolution_clauses
governing_law_clauses
renewal_clauses
indemnification_clauses
```

- Use RAG: retrieve relevant chunks from the vector DB before passing to LLM
- System prompt:

```
You are a legal clause extractor. Given the following contract text, identify and extract
each of the listed clause types. For each clause found, return:
- clause_type: the type of clause
- text: the exact text of the clause
- location: approximate location (beginning/middle/end)
- present: true/false whether this clause exists
```

- Add this as a node in the main LangGraph workflow

**Deliverable:** Agent returns a structured JSON of all clauses found in a contract.

---

## Phase 3 — Risk and Compliance Agents (Days 23–29)

---

### Day 23 — Risk Assessment Agent (Agent 3)

**Goal:** Build the agent that identifies risky clauses.

- Create `agents/risk_agent.py`
- The risk agent analyzes each extracted clause and assigns a risk level
- Risk categories to detect:

```
UNLIMITED_LIABILITY      — no cap on damages
ONE_SIDED_TERMINATION    — only one party can terminate
AUTOMATIC_RENEWAL        — contract auto-renews without notice
BROAD_IP_ASSIGNMENT      — assigns all work, even prior work
UNILATERAL_MODIFICATION  — one party can change terms unilaterally
EXCESSIVE_PENALTIES      — late fees or penalties that seem disproportionate
BROAD_CONFIDENTIALITY    — overly broad definition of confidential information
```

- For each risk found, return:

```json
{
  "risk_type": "UNLIMITED_LIABILITY",
  "severity": "HIGH",
  "clause_text": "...",
  "explanation": "This clause imposes unlimited financial liability on you...",
  "suggestion": "Negotiate a liability cap equal to the contract value."
}
```

- Add as a node in the LangGraph workflow, receiving clause output from Agent 2

**Deliverable:** Agent flags risky clauses with severity levels and plain-English explanations.

---

### Day 24 — RAG Knowledge Base Setup

**Goal:** Build the legal knowledge base that the Compliance Agent will use.

- Create a `knowledge_base/` folder
- Source and store these documents (plain text or PDF):
  - Sample NDA templates (can be publicly available)
  - Sample service agreement templates
  - Summary of GDPR key provisions (public info)
  - Summary of basic contract law principles
  - Common fair contract standards

- Build `services/knowledge_base_ingester.py`
- Process all knowledge base documents through the same ingestion pipeline used for contracts
- Tag each embedding with its source document type for metadata filtering
- Store in a separate vector DB collection called `legal_knowledge`

**Deliverable:** Legal knowledge base loaded into vector DB with metadata tags.

---

### Day 25 — Compliance Agent (Agent 4)

**Goal:** Build the agent that checks contracts against legal standards.

- Create `agents/compliance_agent.py`
- The compliance agent:
  1. Receives the extracted clauses from Agent 2
  2. Retrieves relevant legal standards from the `legal_knowledge` vector collection
  3. Compares clauses against retrieved standards
  4. Flags compliance issues

- Categories to check:

```
missing_required_clauses    — clauses that should be present but aren't
potentially_illegal_terms   — terms that may violate standard legal principles
gdpr_concerns               — data handling and privacy issues
```

- Return format:

```json
{
  "issue_type": "MISSING_REQUIRED_CLAUSE",
  "clause_type": "dispute_resolution",
  "severity": "MEDIUM",
  "explanation": "This contract has no dispute resolution mechanism...",
  "recommendation": "Add a clause specifying arbitration or mediation process."
}
```

**Deliverable:** Agent cross-references contract against legal knowledge base and flags issues.

---

### Day 26 — Q&A Agent (Agent 5)

**Goal:** Build the conversational agent that answers questions about the contract.

- Create `agents/qa_agent.py`
- The Q&A agent:
  1. Takes a natural language question from the user
  2. Retrieves the most relevant chunks from the contract's embeddings
  3. Answers the question grounded in the contract text

- System prompt:

```
You are a legal document assistant. Answer questions about the provided contract accurately
and in plain English. Always cite which part of the contract your answer is based on.
If the answer is not found in the contract, say so explicitly — never make up an answer.
```

- Create `api/qa.py` with endpoint `POST /contracts/{contract_id}/ask`
- Note: this endpoint will be connected to the full **conversation history system** in Phase 6 (Day 46) — for now, build it to function statelessly, one question at a time

**Deliverable:** Ask "Can this contract be terminated early?" and get an accurate, cited answer.

---

### Day 27 — Main LangGraph Orchestration Workflow

**Goal:** Connect all five agents into one complete analysis workflow.

- Create `agents/workflow.py`
- Build the complete LangGraph workflow:

```
START
  → parsing_agent        (identify doc type, parties)
  → clause_agent         (extract all clauses)
  → risk_agent           (analyze clause risks)
  → compliance_agent     (check against standards)
  → summary_generator    (generate plain-English summary)
END
```

- Add conditional edges: if `raw_text` is empty, route to an error node
- Add a summary generation node that creates a final plain-English report
- Create `api/analysis.py` with `POST /contracts/{contract_id}/analyze`
- This endpoint triggers the full workflow and stores results

**Deliverable:** Call `/analyze`, all five agents run in sequence, complete analysis saved to DB.

---

### Day 28 — Negotiation Suggestions Feature

**Goal:** Add negotiation tips to the analysis output.

- Extend the risk agent's output to include negotiation suggestions for every HIGH and MEDIUM risk
- Create a dedicated `negotiation_advisor` node in LangGraph
- For each flagged risk, generate:

```json
{
  "original_clause": "...",
  "risk": "UNLIMITED_LIABILITY",
  "suggested_revision": "Suggest adding: Notwithstanding the above, the total liability of either party shall not exceed the total fees paid in the 12 months preceding the claim.",
  "negotiation_tip": "Frame this as a standard industry practice, not as distrust."
}
```

- Add this section to the final analysis report

**Deliverable:** Analysis report includes specific, actionable negotiation language for every risk.

---

### Day 29 — Error Handling, Logging, and LangSmith Setup

**Goal:** Make the system production-ready with observability.

- Set up LangSmith:
  - Create account at `smith.langchain.com`
  - Add `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true` to `.env`
  - Every LangGraph run will now appear in LangSmith dashboard

- Add structured logging throughout the backend, specifically logging which LLM provider served each request, since this matters for tracking free-tier usage:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Starting analysis for contract_id=%s", contract_id)
logger.info("LLM call served by provider=%s for contract_id=%s", provider_name, contract_id)
```

- Add global exception handler in FastAPI:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled error: %s", str(exc))
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
```

- Confirm the GLM → Groq fallback built on Day 20 is actually triggering correctly under load — deliberately exhaust the Z.AI free-tier rate limit in a test environment (or mock a 429 response) and verify the pipeline keeps working via Groq's Llama 3.3 70B without the user noticing any disruption

**Deliverable:** All agent runs visible in LangSmith. API never returns a 500 without logging the error.

---

## Phase 4 — Frontend Development (Days 30–39)

---

### Day 30 — Frontend Architecture and Routing

**Goal:** Build the full page structure and routing.

- Set up React Router with these routes:

```
/                   → Landing page
/login              → Login (now includes phone OTP step from Phase 2A)
/register           → Register
/dashboard          → Dashboard (contract list)
/contracts/upload   → Upload new contract
/contracts/:id      → Contract detail and analysis
/contracts/:id/ask  → Q&A chat interface
/settings/security  → Phone-based 2FA and Active Sessions management (built Days 12-15)
/history            → Full activity history (built Phase 6)
```

- Create a `PrivateRoute` component that redirects to `/login` if not authenticated, and respects the idle-timeout logic from Day 11
- Set up Zustand store for authentication state:

```typescript
interface AuthStore {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
}
```

- Create the shared `Layout` component with sidebar navigation, including links to Security Settings and Activity History

**Deliverable:** All routes exist and navigate correctly. Auth state persists across page refreshes.

---

### Day 31 — Authentication Pages (Including Phone OTP Flow)

**Goal:** Build the Login and Register pages, fully wired to the Phase 2A backend.

- Build `LoginPage.tsx`:
  - Email and password fields using `react-hook-form`
  - Validation: required fields, valid email format
  - Handle the `requires_2fa` response by showing the SMS code entry screen, with the masked phone number and auto-fill support
  - On success: store token in Zustand, redirect to `/dashboard`
  - On error: show error message from API

- Build `RegisterPage.tsx`:
  - Same fields plus a "Confirm Password" field
  - Client-side password match validation
  - On success: auto-login and redirect to `/dashboard`, with a friendly prompt suggesting the user add their phone number in Security Settings to enable 2FA

- Style both pages with Tailwind — clean, centered card layout

**Deliverable:** Register a new user, log in (with SMS OTP if 2FA is enabled), see the dashboard. Logout clears the token and revokes the session.

---

### Day 32 — Dashboard Page

**Goal:** Build the contracts list dashboard.

- Create `DashboardPage.tsx`
- Use React Query to fetch `GET /contracts/`:

```typescript
const { data: contracts, isLoading } = useQuery({
  queryKey: ['contracts'],
  queryFn: fetchContracts,
});
```

- Display contracts in a table/card list with:
  - Contract filename
  - Upload date
  - Analysis status (Not Analyzed / Analyzing / Complete / Failed)
  - Quick action buttons: Analyze, View, Delete

- Add empty state: "No contracts yet. Upload your first contract."
- Add a prominent "Upload Contract" button

**Deliverable:** Dashboard shows all user contracts with real data from the API.

---

### Day 33 — File Upload Component

**Goal:** Build the contract upload experience.

- Create `UploadPage.tsx` with a drag-and-drop upload zone:

```typescript
// Use react-dropzone
const { getRootProps, getInputProps, isDragActive } = useDropzone({
  accept: { 'application/pdf': ['.pdf'] },
  maxSize: 10 * 1024 * 1024, // 10MB
});
```

- Show upload progress bar using Axios's `onUploadProgress`
- After upload completes, show the contract in the list with "Not Analyzed" status
- Optionally: show a button to immediately start analysis

**Deliverable:** Drag a PDF into the upload zone, watch the progress bar, see it appear in the dashboard.

---

### Day 34 — Contract Detail Page — Structure

**Goal:** Build the skeleton of the contract analysis page.

- Create `ContractDetailPage.tsx`
- Fetch contract data and analysis results from the API
- Build a two-panel layout:
  - **Left panel:** Contract metadata, navigation tabs
  - **Right panel:** Analysis content based on active tab

- Create these tab sections (content added over next two days):
  - Overview
  - Clauses
  - Risk Analysis
  - Compliance
  - Negotiation Tips
  - Q&A

- Add an "Analyze Now" button that calls `POST /contracts/:id/analyze`
- Show a loading spinner while analysis is running

**Deliverable:** Contract detail page loads, tabs switch, analyze button triggers the workflow.

---

### Day 35 — Contract Detail Page — Analysis Display

**Goal:** Display all analysis results clearly.

- **Overview Tab:** Document type, parties involved, jurisdiction, effective date, one-paragraph plain-English summary
- **Clauses Tab:** Expandable accordion for each clause type found; show clause text on expand
- **Risk Analysis Tab:** Color-coded risk cards — red for HIGH, orange for MEDIUM, yellow for LOW. Each card shows the risk type, explanation, and the flagged clause text.
- **Compliance Tab:** Table of compliance issues with severity badges
- **Negotiation Tips Tab:** For each risk, show the original clause, the suggested revision, and the negotiation tip side by side

**Deliverable:** Complete analysis is readable and visually clear to a non-lawyer user.

---

### Day 36 — Q&A Chat Interface

**Goal:** Build the conversational Q&A feature for contracts.

- Create `QAPage.tsx` with a chat UI
- Features:
  - Message bubbles (user on right, AI on left)
  - Input field at the bottom with send button
  - Loading indicator while waiting for AI response
  - Scroll to latest message automatically

- Integrate with `POST /contracts/:id/ask`
- Show suggested questions as chips when chat is empty:
  - "Can this contract be terminated early?"
  - "What are the payment terms?"
  - "What happens if I miss a deadline?"
- Note: this chat will become persistent (saved and resumable) once connected to the conversation history system in Phase 6

**Deliverable:** Ask a question about a contract in natural language and get a cited answer.

---

### Day 37 — Frontend Polish and UX

**Goal:** Improve the overall user experience.

- Add toast notifications (install `react-hot-toast`):
  - Success: "Analysis complete"
  - Error: "Upload failed — file too large"
  - Info: "Analysis started, this may take a minute"

- Add loading skeletons instead of blank screens while data loads
- Add confirmation dialogs before destructive actions (delete contract)
- Make the layout fully responsive for tablet and mobile
- Add empty states for every list view
- Add document title updates using `useEffect` with `document.title`

**Deliverable:** Smooth, polished UX with feedback at every step.

---

### Day 38 — Contract Comparison Feature — Backend

**Goal:** Build the diff engine for comparing two contracts.

- Create `api/comparison.py` with endpoint `POST /contracts/compare`
- Accept two contract IDs in the request body
- Compare at two levels:
  1. **Clause level:** Which clause types are present in one but not the other?
  2. **Text level:** For clauses present in both, what changed in the text?

- Use Python's `difflib.SequenceMatcher` for text-level diff
- Return a structured diff result:

```json
{
  "added_clauses": ["intellectual_property"],
  "removed_clauses": ["renewal"],
  "modified_clauses": {
    "liability": { "old_text": "...", "new_text": "...", "diff": [...] }
  }
}
```

**Deliverable:** API endpoint correctly identifies what changed between two contract versions.

---

### Day 39 — Contract Comparison Feature — Frontend

**Goal:** Build the comparison UI.

- Create `ComparisonPage.tsx`
- Let the user select two contracts from a dropdown
- Display results in a side-by-side view:
  - Green highlight: added text
  - Red highlight: removed text
  - Yellow highlight: modified text
- Show a summary at the top: "3 clauses changed, 1 clause added, 1 clause removed"
- Add a "What changed in the risk profile?" section using the risk agent

**Deliverable:** Select two contracts, see a clear visual diff of what changed.

---

## Phase 5 — Contract Memory and Search (Days 40–44)

---

### Day 40 — Semantic Search Backend

**Goal:** Build the ability to search across all contracts.

- Create `api/search.py` with endpoint `GET /contracts/search?q=indemnity+clause`
- Implementation:
  1. Embed the search query using the same embedding model
  2. Perform a vector similarity search across all contracts belonging to the user
  3. Group results by contract and return the top 5 contracts with the most relevant chunks

- Add metadata filtering: filter by document type, date range, risk level
- Return results with the matching chunk highlighted

**Deliverable:** Search "indemnity clause" and get all contracts that contain relevant text, ranked by relevance.

---

### Day 41 — Semantic Search Frontend

**Goal:** Build the search UI.

- Create `SearchPage.tsx`
- Add a prominent search bar at the top of the dashboard
- Display results as cards showing:
  - Contract filename
  - Matching excerpt with the relevant text bolded
  - Document type badge
  - Risk level indicator

- Add filters panel: document type, date range, risk level
- Add debouncing to avoid firing a search on every keystroke

**Deliverable:** Type in the search bar, get relevant contract results within 1–2 seconds.

---

### Day 42 — Async Background Processing

**Goal:** Make the analysis pipeline run in the background instead of blocking the request.

- Make the analysis workflow run asynchronously using FastAPI's `BackgroundTasks`:

```python
@router.post("/contracts/{contract_id}/analyze")
async def analyze_contract(contract_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_analysis_workflow, contract_id)
    return {"message": "Analysis started", "contract_id": contract_id}
```

- The frontend polls `GET /contracts/{contract_id}` every 3 seconds to check status
- Add database query optimizations: index `contract_id` on the `analyses` table

**Deliverable:** Analyze button returns immediately. Frontend shows "Analyzing..." and updates when done.

---

### Day 43 — Performance Optimization

**Goal:** Make the overall application faster ahead of the history/architecture work in Phase 6.

- Cache analysis results in memory using `functools.lru_cache` for repeated fetches
- Add database connection pooling configuration review
- Add response compression (gzip) middleware to FastAPI
- Profile the slowest API endpoints and address any obvious N+1 query issues

**Deliverable:** Noticeably faster dashboard and contract detail page loads, confirmed with before/after timing.

---

### Day 44 — Free AI Stack Resilience and Rate Limit Monitoring

**Goal:** Build real visibility into the free-tier AI usage this entire project depends on and confirm the fallback chain works under sustained load.

- Create `services/ai_usage_monitor.py`:
  - A small scheduled job (APScheduler, running daily) that logs estimated daily API call counts and flags if the project is approaching the free tier's 1,500 requests/day limit on Google AI Studio
  - Log a warning to the console (and optionally email) when the 24-hour request count exceeds 1,200 (80% of the free daily cap)
- Add a `GET /admin/ai-usage` endpoint (protected, for your own use only) that surfaces the estimated daily request counts for both Gemini (primary) and Groq (fallback) so you never get surprised mid-demo by a quota wall
- Document the **upgrade plan** in `ARCHITECTURE.md` under a new "Free AI Stack Operations" section: what to do when the Google AI Studio free tier runs low (link a billing account to Google Cloud to unlock pay-as-you-go at $1.50/1M input tokens — one of the cheapest rates available for a frontier model) and what to do if Gemini's free-tier terms ever change (the Groq fallback built on Day 20 buys time to react, but isn't a permanent embedding substitute since Groq doesn't serve an embedding endpoint on its free tier — note this explicitly as a known limitation)
- Stress-test the Groq fallback path properly, not just with a single mocked 429: simulate a sustained period (a few minutes of continuous requests) where every Gemini call fails, and confirm the agent pipeline keeps completing analyses end-to-end on Groq alone without manual intervention

**Deliverable:** A working usage dashboard for both free AI providers, a documented upgrade plan so a rate-limited key is a five-minute fix rather than a surprise outage, and a confirmed, sustained (not just single-request) fallback path to Groq.

---

## Phase 6 — Activity History and Conversation Architecture (Days 45–48)

**Why this phase exists:** A platform that holds someone's legal documents and private conversations about them needs more than a simple "audit log" bolted on at the end. This phase designs and builds a proper history system: every login, upload, analysis, search, and Q&A conversation is recorded, organized, and made available back to the user in a structured, trustworthy way — not just for compliance, but so the user can return weeks later and pick up exactly where they left off.

---

### Day 45 — History and Conversation Data Architecture

**Goal:** Design the complete data model for activity history and persistent conversations before building it.

- Extend the existing `audit_logs` table design and formalize the event taxonomy:

```
EVENT TYPES
  USER_REGISTERED
  USER_LOGIN
  USER_LOGIN_FAILED
  USER_LOGOUT
  SESSION_EXPIRED
  TWO_FACTOR_ENABLED
  TWO_FACTOR_DISABLED
  TWO_FACTOR_LOGIN_VERIFIED
  CONTRACT_UPLOADED
  CONTRACT_ANALYZED
  CONTRACT_DELETED
  CONTRACT_VIEWED
  QA_MESSAGE_SENT
  COMPARISON_RUN
  SEARCH_PERFORMED
```

- Design the **conversation** tables, separate from the generic audit log, since a Q&A conversation is structured data the user will want to revisit, not just a log line:

```
conversations
  id
  user_id
  contract_id
  title              (auto-generated from first question, editable by user)
  created_at
  last_message_at

conversation_messages
  id
  conversation_id
  role               (user / assistant)
  content
  cited_clause_refs  (json — which clauses the answer drew from)
  created_at
```

- Document the difference clearly in `ARCHITECTURE.md`: `audit_logs` is a flat, append-only security/compliance trail; `conversations` is structured, user-facing, and meant to be browsed and resumed.

**Deliverable:** A reviewed data model covering both the security audit trail and the user-facing conversation history.

---

### Day 46 — Activity History Backend

**Goal:** Implement consistent audit logging across the entire application, and the conversation persistence layer.

- Create a single `services/audit_logger.py` utility used everywhere, so logging is never inconsistent:

```python
def log_activity(user_id: int, event_type: str, resource_id: int = None, metadata: dict = None):
    ...
```

- Go back through every endpoint built so far (auth, contracts, analysis, search, comparison) and add the appropriate `log_activity()` call — this is a deliberate retrofit pass to make sure nothing built earlier was missed
- Update `POST /contracts/{contract_id}/ask` (built Day 26) to:
  - Create a `conversations` record on the first message for a contract (or reuse the existing one)
  - Save every question and answer as `conversation_messages`, including which clauses the answer cited
- Add endpoints:
  - `GET /history` — paginated, filterable activity feed for the current user
  - `GET /conversations` — list of all past Q&A conversations, across all contracts
  - `GET /conversations/{id}` — full message history for one conversation

**Deliverable:** Every meaningful action across the platform is now logged, and every Q&A conversation is saved and retrievable later, not lost when the page is refreshed.

---

### Day 47 — Activity History Frontend

**Goal:** Give users a clear, browsable view of their own history.

- Build `HistoryPage.tsx` at `/history`:
  - Timeline view of all activity, most recent first
  - Filter by event type (logins, uploads, analyses, searches) and date range
  - Each entry is plain English, not raw event codes: "You uploaded Freelance_Agreement.pdf" rather than `CONTRACT_UPLOADED`
- Build `ConversationsPage.tsx`:
  - List of all past conversations, grouped by contract, showing the title and last message time
  - Clicking a conversation reopens the full Q&A thread in the same chat UI built on Day 36, fully scrollable and resumable
- Add a "Resume conversation" entry point directly from the Contract Detail page's Q&A tab, so returning to a contract shows past questions instead of a blank chat

**Deliverable:** A user can see a full, readable history of everything they've done, and reopen any past document conversation exactly where they left it.

---

### Day 48 — History Privacy, Retention, and Data Export

**Goal:** Make sure the history system itself respects user trust and gives the user control over their own data.

- Confirm every history and conversation query is scoped strictly to `user_id` — write a specific test that one user can never see another user's history or conversations via the API
- Add a **data export** feature: `GET /account/export` — generates a JSON (or PDF, using the existing pdf skill patterns) containing all of a user's contracts, analyses, conversations, and activity history, downloadable on request
- Add a **data retention setting** in Security Settings: let the user choose how long activity history is kept (e.g., 90 days, 1 year, forever) and implement a scheduled job that respects this setting
- Add an **account deletion** flow: `DELETE /account` permanently removes the user's documents, conversations, history, and sessions, with a confirmation step requiring password + a fresh OTP sent to the registered phone

**Deliverable:** The history system itself is provably private, exportable on demand, and fully deletable — reinforcing the trust principles laid out in Part 1.

---

## Phase 7 — DevOps and Deployment (Days 49–55)

---

### Day 49 — Complete Docker Compose Setup

**Goal:** Run the entire stack with one command.

- Update `docker-compose.yml` with all services:

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres]
  postgres:
    image: postgres:15
    volumes: [postgres_data:/var/lib/postgresql/data]
  pgadmin:
    image: dpage/pgadmin4
    ports: ["5050:80"]
```

- Add health checks to each service
- Use Docker networks so services communicate by service name, not localhost
- Write a `Makefile` with shortcuts:

```makefile
up:    docker-compose up -d
down:  docker-compose down
logs:  docker-compose logs -f backend
```

**Deliverable:** `make up` starts everything. `make down` stops everything cleanly.

---

### Day 50 — Environment Configuration and Secrets Management

**Goal:** Handle secrets and config properly for multiple environments.

- Create three environment configurations:
  - `development` — local DB, verbose logging, debug mode on
  - `staging` — cloud DB, moderate logging
  - `production` — cloud DB, minimal logging, strict security headers

- Use `pydantic-settings` to load the correct config based on `APP_ENV` environment variable
- Never commit secrets to Git: add `.env` files to `.gitignore`
- Ensure the SMS provider API credentials (e.g., MSG91 Auth Key or Twilio Account SID/Auth Token) and the DLT-approved sender header/template ID are treated as sensitive configuration alongside JWT signing keys — documented separately with rotation guidance, and never exposed in frontend code or logs
- Write a `secrets.example.md` documenting all required environment variables with descriptions

**Deliverable:** Application loads the correct settings based on which `.env` file is present.

---

### Day 51 — GitHub Actions CI Pipeline

**Goal:** Automate testing on every push.

- Create `.github/workflows/ci.yml`
- Pipeline steps:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    steps:
      - checkout
      - setup Python 3.11
      - install dependencies
      - run alembic migrations
      - run pytest
      - run frontend lint
```

- Write at minimum 15 backend tests covering:
  - User registration and login
  - Session refresh and expiry
  - Phone OTP setup and login verification
  - File upload validation
  - Contract creation
  - Analysis workflow (mock LLM calls)
  - History and conversation isolation between users

**Deliverable:** Every push to `main` runs all tests automatically. A failed test blocks merge.

---

### Day 52 — Cloud Deployment — Database and Storage

**Goal:** Set up managed cloud infrastructure.

Use Railway or Render for simplicity:

- **Option A (Railway):**
  - Create a PostgreSQL service on Railway
  - Set all environment variables in the Railway dashboard
  - Note the database URL

- **Option B (AWS RDS):**
  - Launch a PostgreSQL RDS instance (free tier)
  - Configure security group to allow inbound on port 5432
  - Note the connection string

- Run Alembic migrations against the cloud database (including session, phone OTP, and conversation tables)
- Test connecting to the cloud DB from your local machine

**Deliverable:** Cloud PostgreSQL database running with all tables created.

---

### Day 53 — Cloud Deployment — Backend

**Goal:** Deploy the FastAPI backend to the cloud.

- Deploy to Railway or Render:
  - Connect GitHub repository
  - Set environment variables: `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `SECRET_KEY`, `SMS_PROVIDER_API_KEY`, `SMS_DLT_SENDER_ID`, `SMS_DLT_TEMPLATE_ID`, etc.
  - Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

- Verify the deployed API:
  - `GET https://your-app.railway.app/health` returns 200
  - `POST /auth/login` works with cloud DB, including the phone OTP step actually sending a real SMS to an Indian number via the deployed, DLT-compliant provider credentials
  - File uploads work (configure cloud storage or use ephemeral for now)

**Deliverable:** FastAPI backend running at a public HTTPS URL.

---

### Day 54 — Cloud Deployment — Frontend, and Auth Rate Limiting

**Goal:** Deploy the React frontend, and close the rate-limiting gap flagged on Day 15.

- Deploy to Vercel:
  - `npm install -g vercel`
  - `vercel` from the `frontend/` directory
  - Set `VITE_API_URL` environment variable to the backend URL from Day 53

- Add rate limiting to auth and OTP endpoints (prevent brute force, and prevent SMS-cost abuse from repeated OTP requests):

```python
# install slowapi
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(...): ...

@app.post("/auth/2fa/login-verify")
@limiter.limit("5/minute")
async def verify_2fa(...): ...

@app.post("/auth/2fa/resend-otp")
@limiter.limit("3/5minutes")
async def resend_otp(...): ...
```

- Verify:
  - Frontend loads at Vercel URL
  - Login (with real SMS OTP) works against the deployed backend
  - Upload a PDF and run analysis end-to-end on the live deployment

**Deliverable:** Full application accessible at a public URL. End-to-end flow, including SMS-based OTP login, works.

---

### Day 55 — OpenTelemetry and Monitoring

**Goal:** Add production monitoring.

- Install:

```
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
```

- Instrument the FastAPI app:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)
```

- Track these metrics:
  - API request latency per endpoint
  - Database query duration
  - Analysis workflow duration
  - Error rates
  - Failed login and failed OTP verification rates (a security-relevant metric, not just performance) — also useful for catching SMS delivery failures from the provider

- Send traces to LangSmith (already configured) and optionally Grafana Cloud free tier

**Deliverable:** API latency, error rates, and suspicious auth activity all visible in a monitoring dashboard.

---

## Phase 8 — Testing, Polish, and Documentation (Days 56–62)

---

### Day 56 — Comprehensive Backend Testing

**Goal:** Achieve solid test coverage across the whole backend, including the new security and history systems.

- Write tests for all API endpoints using `pytest` + `httpx`
- Use a separate test database (in-memory SQLite or a test PostgreSQL DB)
- Mock all external calls (Google Gemini API, Groq API, vector DB) using `pytest-mock`
- Test these scenarios:
  - Invalid file type upload (should return 400)
  - Upload a valid PDF (should return 200 with contract ID)
  - Run analysis on a nonexistent contract (should return 404)
  - Ask a question without first running analysis (should return 400)
  - Access token expiry (should return 401)
  - Idle session expiry (should return `SESSION_EXPIRED`)
  - Login with 2FA enabled but no code provided (should return `requires_2fa`)
  - Login with a wrong OTP code (should fail, and be rate-limited after repeated attempts)
  - OTP resend respects the cooldown window and does not allow rapid-fire SMS requests
  - Adding a non-Indian phone number (wrong length, wrong starting digit, or non-+91 format) is rejected with a clear error and never reaches the SMS provider call
  - One user attempting to read another user's history or conversation (should return 403/404)

**Deliverable:** `pytest` passes with at least 30 tests covering happy paths, error cases, and security edge cases.

---

### Day 57 — Agent Prompt Refinement

**Goal:** Improve the quality of agent outputs.

- Test each agent with at least 5 real contract PDFs (find free samples online)
- For each agent, document where it performs poorly
- Refine the system prompts to address those failures
- Add few-shot examples to the prompts for edge cases
- Test the Q&A agent specifically — it should say "I don't know" rather than hallucinate
- Update the LangGraph conditional edges to handle malformed LLM outputs gracefully

**Deliverable:** All five agents produce noticeably better outputs on the specific failure cases found during testing.

---

### Day 58 — Cross-Document Consistency Testing (USP Verification)

**Goal:** Specifically test and prove differentiator #5 from the USP table — that the platform applies the same rigorous checklist to every document, every time, regardless of how it's phrased or structured — rather than just fixing isolated prompt failures as they're found.

- Build a small **regression test set**: at least 10 real contracts spanning different types (NDA, rental, employment, freelance, SaaS terms), each run through the full five-agent pipeline
- For each contract, record the full output (clauses found, risks flagged, compliance issues, summary) as a baseline snapshot
- Write `tests/test_agent_consistency.py`:
  - Re-run the same 10 contracts 2–3 times each and confirm the same clause types and risk categories are consistently detected (some variation in exact wording is expected from the LLM, but the same clause types must not randomly disappear between runs)
  - Confirm every contract's analysis includes checks for **all nine clause types** from Day 22, not a subset, regardless of document length or formatting
  - Confirm severity ratings (HIGH/MEDIUM/LOW) for the same type of risk stay consistent across different contracts containing a similar clause (e.g., an uncapped liability clause should not be HIGH in one contract and LOW in another with no clear reason)
- Document any inconsistencies found, and if needed, tighten the prompts further (e.g., adding an explicit checklist instruction: "You must evaluate all nine clause types below, even if a clause type is not present — report `present: false` explicitly rather than omitting it")
- Add this regression test set to the CI pipeline (extending Day 51) so future prompt changes can be checked against the same baseline before merging

**Deliverable:** A documented, repeatable test suite proving the platform's analysis quality does not degrade or vary unpredictably across different documents or repeated runs — turning "consistency" from a marketing claim into a measured, demonstrable property of the system.

---

### Day 59 — Frontend Testing

**Goal:** Add component and integration tests to the frontend.

- Install `vitest` and `@testing-library/react`
- Write tests for:
  - `LoginPage` — form renders, submit calls the API, OTP step appears when required, error message shows on failure
  - `UploadPage` — file type validation rejects non-PDFs
  - `ContractDetailPage` — analysis results render correctly given mock data
  - `QAPage` — sending a message appends it to the chat and persists across a refresh
  - `HistoryPage` — activity feed renders and filters correctly

- Add end-to-end test for the critical user journey using Playwright:
  1. Register
  2. Add and verify a phone number to enable 2FA
  3. Log out and log back in through the full SMS OTP flow (mock the SMS provider in test)
  4. Upload a contract
  5. Run analysis
  6. View risk report
  7. Ask a question, refresh the page, confirm the conversation is still there
  8. Check the history page shows all of the above actions

**Deliverable:** Frontend test suite passes. Critical user journey, including security and history features, covered by E2E test.

---

### Day 60 — Security Hardening

**Goal:** Address common security vulnerabilities across the full application.

- Add security headers to FastAPI:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(CORSMiddleware, allow_origins=["https://your-frontend.vercel.app"], ...)
```

- Validate that users can only access their own contracts, conversations, and history (check `user_id` on every query — re-confirm this across every endpoint built since Day 46)
- Confirm OTP codes and refresh tokens are hashed at rest, never logged in plain text anywhere (including third-party SMS provider dashboards/webhooks)
- Sanitize all file upload names to prevent path traversal
- Run a basic dependency vulnerability scan (`pip-audit`, `npm audit`) and resolve any high-severity findings

**Deliverable:** Security checklist complete. Users cannot access other users' data, sessions, or history under any tested scenario.

---

### Day 61 — README, Architecture Docs, and Demo Data

**Goal:** Write documentation that makes the project impressive to recruiters, and seed it with realistic data.

- Update the `README.md` with:
  - Project description and problem statement (from Part 1 of this plan)
  - Architecture diagram, now including the session/phone-OTP service and the history/conversation subsystem
  - Tech stack with version numbers
  - Getting started guide (clone → configure `.env` → `docker-compose up`)
  - Screenshots of the UI, including the Security Settings and History pages
  - Links to the live deployment

- Write `ARCHITECTURE.md` covering: the agent workflow, the session and phone OTP design, and the history/conversation data model
- Create `scripts/seed_demo.py`:
  1. Creates a demo user with a pre-verified demo Indian phone number for 2FA (use the SMS provider's test/sandbox number so evaluators can try the flow without incurring real SMS costs; document this clearly in the README, along with a note that only Indian numbers can be used to set up 2FA on this platform)
  2. Uploads 5 sample contracts and runs full analysis on each
  3. Generates a few sample Q&A conversations so the History and Conversations pages aren't empty on first look
- Add a "Try Demo" path on the login page

**Deliverable:** A README and architecture doc a hiring manager can read in minutes, plus a live demo that already has realistic data and conversation history in it.

---

### Day 62 — Final Performance Pass and Portfolio Launch

**Goal:** Final load testing, then package everything for maximum career impact.

**Morning — Performance and Final Review:**
- Use `locust` to run a basic load test simulating 10 concurrent users uploading and analyzing contracts
- Run `lighthouse` audit on the frontend and resolve any performance issues
- Final check: upload a 20-page contract and confirm full analysis completes within 60 seconds
- Run the full test suite one final time: all tests pass

**Afternoon — Portfolio Artifacts:**
- Write a 500-word project case study covering: the problem, the solution, the security architecture (sessions, phone-based 2FA), the history architecture, and the technical challenges solved
- Record a 3-minute demo video walking through: upload → analysis → Q&A → history → security settings with phone OTP login
- Take high-quality screenshots of every page

**Evening — Launch:**
- Push the final version to GitHub
- Verify the live deployment works end-to-end
- Update your LinkedIn with the project
- Add to your resume under Projects with the tech stack and GitHub link

---

## Summary Table

| Phase | Days | Focus |
|---|---|---|
| 1 | 1–7 | Foundation, backend setup, Docker, React init, basic auth |
| **2A (NEW)** | **8–15** | **Sessions, auto-logout on inactivity, Phone-based (SMS OTP) Two-Factor Authentication** |
| 2B | 16–22 | PDF extraction, chunking, embeddings (free Chinese embedding model), LangGraph, Agents 1–2 |
| 3 | 23–29 | Agents 3–5, RAG knowledge base, full workflow, observability |
| 4 | 30–39 | Full frontend: auth + phone OTP, dashboard, upload, analysis UI, Q&A, comparison |
| 5 | 40–44 | Semantic search, async performance, free AI stack resilience and usage monitoring |
| **6 (EXPANDED)** | **45–48** | **Full activity history architecture, persistent conversations, privacy and data export** |
| 7 | 49–55 | Docker, CI/CD, cloud deployment, rate limiting, monitoring |
| 8 | 56–62 | Testing, prompt refinement, consistency verification, security, docs, demo data, launch |

**Total: 62 days** (increased from the original 50-day plan by 12 days: 8 days for Phase 2A — Sessions and Phone-Based Two-Factor Authentication; 2 net additional days for expanding the original single-day audit log task into the full Phase 6 activity history and conversation architecture; 1 additional day in Phase 8 to split prompt refinement into a dedicated cross-document consistency testing day; and 1 additional day in Phase 5 to properly monitor and document the free Chinese-model AI stack — specifically the time-limited Embedding-3 token grant — so a depleted free quota never becomes a surprise mid-project outage.)

---

## Tech Stack Reference

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Tailwind CSS, React Query, Zustand |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Vector DB | Supabase Vector (pgvector) or Pinecone |
| AI Agents | LangGraph, LangChain |
| LLM | **Google Gemini 3.5 Flash** via Google AI Studio (free tier: 15 RPM / 1,500 req/day / 1M tokens/min, primary) + Groq Llama 3.3 70B (free tier, automatic fallback for resilience) — $0/month |
| Embeddings | Google Gemini Embedding (`models/gemini-embedding-001`) via same API key (free tier, 768-dimension vectors) |
| PDF Parsing | PyMuPDF, pdfplumber |
| Sessions & Auth | JWT access/refresh tokens, server-side session table, idle-timeout middleware |
| Two-Factor Auth | SMS-delivered OTP via MSG91 or Twilio Verify (India route), DLT-compliant sender registration, Indian (+91) numbers only, hashed OTP codes, Web OTP API auto-fill on mobile |
| History & Conversations | Dedicated `audit_logs` and `conversations`/`conversation_messages` tables |
| Observability | LangSmith, OpenTelemetry |
| Testing | pytest, httpx, Vitest, Playwright |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Deployment | Railway or Render (backend), Vercel (frontend) |
