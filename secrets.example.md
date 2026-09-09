# Environment Configuration & Secrets Management Guide

This document defines the configuration schema, secrets management protocol, and credential rotation procedures for the **AI Legal Document Intelligence Platform (`LegalIntel`)**.

---

## 1. Secrets Management Architecture

The platform adheres to **12-Factor App methodology** and **defense-in-depth principles**:
1. **Dynamic Environment Resolution**: The application loads `.env` files based on the active `APP_ENV` variable (`development`, `staging`, `production`, or `test`).
2. **OS Environment Priority**: Operating system environment variables (injected via Docker Compose, Kubernetes, Railway, or GitHub Actions) always supersede file-based values.
3. **Automated Secrets Redaction**: The backend `Settings` model automatically masks all sensitive keys (`JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `GEMINI_API_KEY`, `LANGCHAIN_API_KEY`, `GOOGLE_CLIENT_SECRET`, `SMTP_PASSWORD`, and database URL credentials) in `__repr__`, `__str__`, and logging output (`masked_dict()`).
4. **Strict Production Validation**: In `APP_ENV=production`, the application refuses to boot if `DEBUG=True` or if `JWT_SECRET_KEY` uses insecure default placeholders or has fewer than 32 characters.
5. **Multi-Tenant & Client Isolation**: Backend secrets are strictly segregated from the client. Zero backend secrets or SMTP credentials are ever passed to the React frontend bundle or client logs.

---

## 2. Master Environment Variables Matrix

| Variable Name | Type | Default Value | Security Tier | Required In | Description |
|---|---|---|---|---|---|
| `APP_ENV` | `str` | `development` | Operational | All | Target runtime: `development`, `staging`, `production`, or `test`. |
| `DEBUG` | `bool` | `true` (dev) / `false` (prod) | Operational | All | Enables FastAPI debug mode and tracebacks. **MUST be `false` in production.** |
| `LOG_LEVEL` | `str` | `DEBUG` (dev) / `INFO` (prod) | Operational | All | Root logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |
| `BACKEND_PORT` | `int` | `8000` | Operational | All | Port where FastAPI uvicorn listens. |
| `FRONTEND_URL` | `str` | `http://localhost:5173` | Operational | All | Canonical frontend origin for redirects and CORS. |
| `CORS_ORIGINS` | `list[str]` | `localhost:5173, 127.0.0.1:5173, localhost:3000` | Sensitive | All | Comma-separated or JSON list of permitted cross-origin domains. |
| `STRICT_SECURITY_HEADERS` | `bool` | `false` (dev) / `true` (prod) | Operational | Staging, Prod | Enforces HSTS, X-Frame-Options DENY, nosniff, and CSP headers. |
| `SECURE_COOKIES` | `bool` | `false` (dev) / `true` (prod) | Operational | Staging, Prod | Sets `Secure=True; SameSite=Strict` on session cookies. |
| `DATABASE_URL` | `str` | `postgresql://...localhost:5433/...` | **Critical Secret** | All | Full SQLAlchemy connection string including user, password, host, port, and DB. |
| `POSTGRES_USER` | `str` | `postgres` | Operational | All | PostgreSQL username. |
| `POSTGRES_PASSWORD` | `str` | `postgres` | **Critical Secret** | All | PostgreSQL database user password. |
| `POSTGRES_DB` | `str` | `legal_ai_db` | Operational | All | Relational database name. |
| `JWT_SECRET_KEY` | `str` | `your-super-secret-key-change-this` | **Critical Secret** | All | 256-bit cryptographically random secret used to sign HS256 auth tokens. |
| `JWT_ALGORITHM` | `str` | `HS256` | Operational | All | Cryptographic algorithm for JWT signing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `int` | `40` | Sensitive | All | Access token validity window (idle timeout synchronization). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `7` | Sensitive | All | Long-lived refresh token validity window. |
| `SESSION_IDLE_TIMEOUT_MINUTES`| `int` | `40` | Sensitive | All | Inactivity window before session revocation. |
| `SMTP_HOST` | `str` | `smtp.example.com` | Sensitive | Staging, Prod | Outbound SMTP server hostname for 2FA OTP emails. |
| `SMTP_PORT` | `int` | `587` | Sensitive | Staging, Prod | SMTP port (`587` for STARTTLS, `465` for SSL, `2525` for Mailtrap). |
| `SMTP_USERNAME` | `str` | `""` | Sensitive | Staging, Prod | SMTP authentication account/username. |
| `SMTP_PASSWORD` | `str` | `""` | **Critical Secret** | Staging, Prod | SMTP password or transactional API key (SendGrid, AWS SES, Resend). |
| `SMTP_FROM_EMAIL` | `str` | `noreply@legalintel.ai` | Sensitive | Staging, Prod | Sender email address appearing on 2FA verification emails. |
| `SMTP_USE_TLS` | `bool` | `true` | Operational | Staging, Prod | Enables STARTTLS negotiation on port 587. |
| `SMTP_USE_SSL` | `bool` | `false` | Operational | Staging, Prod | Enables implicit SSL negotiation on port 465. |
| `GEMINI_API_KEY` | `str` | `""` | **Critical Secret** | All | Google AI Studio API key powering Gemini LLM, Vision OCR & Embeddings. |
| `GEMINI_MODEL` | `str` | `gemini-2.5-flash` | Operational | All | Primary model ID for legal multi-agent inference. |
| `AI_FREE_TIER_DAILY_LIMIT` | `int` | `1500` | Operational | All | Daily request ceiling per Gemini model pool. |
| `AI_WARNING_THRESHOLD_PERCENT`| `float` | `80.0` | Operational | All | Percentage threshold for automated quota warning logs. |
| `LANGCHAIN_TRACING_V2` | `str` | `false` | Operational | Staging, Prod | Enables LangSmith distributed agent tracing. |
| `LANGCHAIN_API_KEY` | `str` | `""` | **Critical Secret** | Staging, Prod | LangSmith API key for telemetry ingestion. |
| `LANGCHAIN_PROJECT` | `str` | `ai-legal-document-intelligence` | Operational | All | LangSmith workspace project partition. |
| `LANGCHAIN_ENDPOINT` | `str` | `https://api.smith.langchain.com` | Operational | All | LangSmith telemetry ingest endpoint. |
| `GOOGLE_CLIENT_ID` | `str` | `""` | Sensitive | Optional | Google OAuth 2.0 Client ID for SSO. |
| `GOOGLE_CLIENT_SECRET` | `str` | `""` | **Critical Secret** | Optional | Google OAuth 2.0 Client Secret for SSO. |
| `CHROMA_PERSIST_DIR` | `str` | `./chroma_data` | Operational | All | Filesystem path where ChromaDB stores vector embeddings. |
| `UPLOAD_DIR` | `str` | `./uploads` | Operational | All | Filesystem directory for staged contract documents. |
| `MAX_UPLOAD_SIZE_MB` | `int` | `10` | Operational | All | Maximum allowed contract file size in megabytes. |

---

## 3. Cryptographic Secret Generation

Never use predictable passwords or hardcoded defaults in staging or production. Generate secrets using cryptographically secure pseudorandom generators:

### 3.1 Generating `JWT_SECRET_KEY` (256-bit / 64-char Hex)
```bash
# Option 1: OpenSSL (Recommended)
openssl rand -hex 32

# Option 2: Python secrets module
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 Generating Secure Database Passwords
```bash
# Generate a 32-character URL-safe string
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## 4. Secret Rotation Procedures & Incident Response

### 4.1 Routine 90-Day Rotation
1. **Google Gemini API Key**:
   - Generate a secondary key in [Google AI Studio](https://aistudio.google.com/).
   - Update `GEMINI_API_KEY` in cloud secret manager (Railway/Render).
   - Verify health checks pass (`GET /health`).
   - Deprecate and delete the old key in Google AI Studio console.
2. **SMTP Credentials / API Key**:
   - Create a new API key in SendGrid / AWS SES / Resend.
   - Update `SMTP_PASSWORD` in the environment configuration.
   - Dispatch a test OTP via `/auth/2fa/request-otp` and verify delivery.
   - Delete the previous API key from the email provider portal.
3. **Database Credentials**:
   - Add a secondary database user or rotate password in PostgreSQL.
   - Update `DATABASE_URL` and redeploy.

### 4.2 Emergency Leak / Compromise Protocol
If a secret is inadvertently committed to version control or compromised:
1. **Immediate Invalidation (T+0 min)**:
   - Immediately revoke the compromised key from the provider portal (Google AI Studio, LangSmith, SendGrid).
   - Invalidate all active user sessions in PostgreSQL:
     ```sql
     UPDATE user_sessions SET is_revoked = TRUE, updated_at = NOW();
     ```
2. **Generate Replacement Secrets (T+5 min)**:
   - Generate a fresh 64-char hex key for `JWT_SECRET_KEY`.
   - Generate a new Google Gemini API key.
3. **Deploy Emergency Environment (T+10 min)**:
   - Inject the new variables into the production cloud dashboard.
   - Trigger zero-downtime rolling redeployment.
4. **Forensic Audit (T+30 min)**:
   - Query `audit_logs` for any anomalies or unauthorized actions during the exposure window:
     ```sql
     SELECT * FROM audit_logs WHERE timestamp >= NOW() - INTERVAL '24 hours' ORDER BY timestamp DESC;
     ```

---

## 5. Platform Deployment Configuration

### 5.1 Docker Compose (Local & Self-Hosted)
Docker Compose automatically loads `.env` from the project root. To run with a specific environment:
```bash
# Running with staging configuration
APP_ENV=staging docker-compose up -d

# Running with production configuration
APP_ENV=production docker-compose up -d
```

### 5.1 Hugging Face Spaces (Docker SDK)
Under your Hugging Face Space **Settings $\rightarrow$ Variables and Secrets**:
1. **New Secret:** `DATABASE_URL` — Cloud PostgreSQL connection URI (e.g. from [Neon](https://neon.tech) or [Supabase](https://supabase.com)).
2. **New Secret:** `GEMINI_API_KEY` — Google AI Studio API key.
3. **New Secret:** `JWT_SECRET_KEY` — 256-bit random cryptographic secret (`openssl rand -hex 32`).
4. **New Variable:** `APP_ENV=production`
5. **New Variable:** `DEBUG=false`
6. **New Variable:** `LOG_LEVEL=INFO`
7. *(Optional)* **New Secrets:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` for live email 2FA dispatch.

### 5.2 Docker Compose (Local / Self-Hosted VPS)

### 5.3 Vercel (Cloud Frontend)
In Vercel project environment variables:
1. Set `VITE_API_URL=https://api.legalintel.ai` (points to deployed FastAPI backend).
2. Note: Frontend never receives `JWT_SECRET_KEY` or backend secrets.

### 5.4 GitHub Actions CI
Under GitHub repository **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**:
- `POSTGRES_PASSWORD`: Test database password.
- `JWT_SECRET_KEY`: Random test signing secret.
- `GEMINI_API_KEY`: CI test mock or staging key.

---

## 6. Pre-Commit Checklist & Leak Prevention

- [x] `.env` and all `.env.*` files (except `.env.example` and `.env.*.example`) are in `.gitignore`.
- [x] Zero API keys or private passwords hardcoded in source code files.
- [x] All backend settings string representations (`__repr__`, `__str__`) utilize `masked_dict()`.
- [x] Production environment enforces `DEBUG=False` and minimum 32-character `JWT_SECRET_KEY`.
- [x] SMTP credentials are encapsulated server-side only in `otp_service.py`.
