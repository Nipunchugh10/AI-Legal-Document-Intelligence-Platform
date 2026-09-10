# 🔐 Security Audit Report — AI Legal Document Intelligence Platform

**Audit basis:** `VIBE_CODED_APP_TEST_SHEET.md` (41 adversarial prompts, OWASP Web + API Top 10)
**Scope:** full backend (FastAPI), frontend (React 19), infra (Docker/HF Spaces/CI), git history, and the **live Hugging Face deployment**.
**Date:** 2026-09-10
**Method:** static code review + live probing of the production Space + git-history forensics. Findings are evidence-backed; categories with no real issue are marked **✅ CLEAN** (no speculative changes were made).

---

## Executive summary

| Severity | Count | Status |
| :--- | :---: | :--- |
| 🔴 Critical | 1 | ✅ Fixed (rotation required by owner) |
| 🟠 High | 3 | ✅ Fixed |
| 🟡 Medium | 1 | ✅ Fixed |
| 🔵 Low / Advisory | 3 | Documented (no code change) |

The application's core security posture is **genuinely strong** — parameterized ORM everywhere (zero SQL injection surface), bcrypt password hashing, DB-backed sessions with idle + absolute expiry, strict server-side multi-tenant `user_id` scoping on 100% of object routes, `secrets`-based OTP generation, robust path-traversal defense on uploads, and audit-log credential scrubbing. The findings below are the exceptions, not the rule.

---

## 🔴 CRITICAL

### C1 — Live Hugging Face **write token** stored in plaintext (`.git/config`)
- **Prompt:** 1 (secrets), 34 (git forensics)
- **Evidence:** the `space` git remote embedded a real HF write token:
  `https://Nipunchugh10:hf_RMCAF…TrWTjH@huggingface.co/spaces/…`
- **Impact:** anyone reading the local repo config (shared machine, backup, screen-share, leaked clone) obtains a **write-scoped** token that can push arbitrary code to the deployed Space — full RCE-on-deploy and defacement.
- **Blast radius (verified):** token is **NOT** in any tracked file and **NOT** in git history — exposure was local `.git/config` only.
- **Fix applied:** rewrote the remote to a credential-free URL (`git remote set-url space https://huggingface.co/…`). Git now prompts for / uses a credential helper instead of storing the secret inline.
- **⚠️ Owner action required (I cannot do this for you):** **rotate this token now** at https://huggingface.co/settings/tokens — a plaintext token must be treated as compromised even after removal.

---

## 🟠 HIGH

### H1 — Unauthenticated database/internal info disclosure via `GET /health/db`
- **Prompt:** 7, 9, 11, 18, 30
- **Evidence (live, unauthenticated):** returned DB host `ep-shy-star-…neon.tech`, `PostgreSQL 16.15 …` full version banner, **every table name**, and the current Alembic revision.
- **Impact:** hands an attacker the exact DB provider/endpoint, server version (CVE targeting), schema map, and migration state — a complete recon package with no auth.
- **Fix applied** (`backend/app/main.py`): anonymous callers now get only `{status, core_tables_healthy, latency_ms}`. Full diagnostics remain available to authenticated admins at `/admin/db-health`, and can be re-enabled publicly only via the new opt-in `EXPOSE_PUBLIC_DIAGNOSTICS` flag (default `False`).

### H2 — Unauthenticated internal metrics via `GET /metrics`
- **Prompt:** 9, 11, 16, 25, 30
- **Evidence (live, unauthenticated):** Prometheus exposition leaking the internal route map, latency percentiles, request/error counters, and auth-anomaly counters (`failed_logins`, `failed_otp_attempts`).
- **Impact:** internal endpoint enumeration + a live oracle for whether brute-force/anomaly thresholds are being tripped.
- **Fix applied** (`backend/app/main.py`): `/metrics` now requires a bearer token matching the new `METRICS_TOKEN` (constant-time compare) **or** `EXPOSE_PUBLIC_DIAGNOSTICS=true`; otherwise returns `404`. The same data stays available to authenticated operators at `/admin/telemetry`.

### H3 — Rate-limit bypass via client-controlled `x-test-client-ip` header
- **Prompt:** 3, 9, 19
- **Evidence:** `get_client_ip()` in `backend/app/core/rate_limit.py` honored the `x-test-client-ip` request header **unconditionally, before** `x-forwarded-for`, in all environments.
- **Impact:** an attacker rotates this header per request to get a fresh rate-limit bucket every time, fully defeating the per-IP limits on `/auth/login`, `/auth/register`, and `/auth/2fa/*` → unlimited credential / OTP brute force.
- **Fix applied:** the test override is now honored **only** when `APP_ENV ∈ {development, test}`. In production/staging it is ignored, so real per-IP limiting cannot be spoofed.

---

## 🟡 MEDIUM

### M1 — Non-constant-time OTP hash comparison
- **Prompt:** 3, 14
- **Evidence:** `otp_service.verify_otp()` compared `otp_entry.otp_hash != submitted_hash` with a plain `!=`.
- **Impact:** low practical exploitability (SHA-256 digests of a 6-digit code, network jitter), but a textbook timing-side-channel on a security comparison.
- **Fix applied:** switched to `hmac.compare_digest(...)`. (Refresh-token verification was already safe — it resolves via an indexed DB `WHERE` on the hash, not a Python compare.)

---

## 🔵 LOW / ADVISORY (reported, no code change)

- **A1 — JWT/refresh tokens in `localStorage`** (`frontend/src/store/useAuthStore.ts`). Standard SPA trade-off; means any XSS = token theft. No stored-XSS sink was found (see CLEAN list), so this is an accepted architectural risk. Migrating to `httpOnly` cookies would be a larger auth redesign — flagged, not silently rewritten.
- **A2 — No secrets/SAST scanning in CI** (`.github/workflows/ci.yml`). Given C1, a `gitleaks`/`detect-secrets` gate and a `bandit`/`semgrep` pass on PRs would have caught the token earlier. Recommended, not added (out of "no speculative changes" scope).
- **A3 — Unpinned dependencies** (`^`/`~` in `frontend/package.json`, `>=` in `requirements.txt`). Intentional for this project; `package-lock.json` **is** committed, so frontend builds are deterministic. Consider pinning backend deps for reproducible images.

---

## ✅ CLEAN — audited, nothing found

| # | Category (prompt) | Evidence it's clean |
| :--- | :--- | :--- |
| P2 | **SQL / NoSQL / OS-command / LDAP / XPath injection** | 100% SQLAlchemy ORM with bound params; the only `subprocess` call (`run_load_test.py`) uses an argument list, `shell=False`, no user input; no `os.system`/`eval`/`exec` on request data. |
| P4 | **Broken access control / IDOR / priv-esc** | Every object route filters `Contract.user_id == current_user.id` (etc.). No `role`/`is_admin` field exists to escalate; "admin" routes expose only the caller's own telemetry. Mass-assignment impossible (Pydantic request schemas, explicit field maps). |
| P5 | **XSS** | Only `dangerouslySetInnerHTML` sink (`SearchPage`) renders server output that is `html.escape()`-d before `<mark>` insertion, with query terms escaped too. `nosniff` + CSP `frame-ancestors` set. |
| P6 | **CSRF** | Stateless Bearer-token auth (no session cookies) → not CSRF-able; state-changing routes require the `Authorization` header. |
| P7 | **Sensitive data exposure** | No PII/secrets in logs; audit metadata scrubbed; plaintext OTP console print is env-guarded to dev/test only; secrets masked in `Settings.__repr__`. |
| P8 | **File upload** | Extension allowlist + size cap + `sanitize_upload_filename()` + `is_relative_to(UPLOAD_DIR)` containment + UUID-prefixed names (no collisions). Stored under a dedicated uploads dir. |
| P12 | **SSRF** | No outbound HTTP built from user input — only the Gemini SDK client. |
| P13 | **XXE / insecure deserialization** | No `pickle`, no `yaml.load`, no XML parsing of user input; DOCX handled by `python-docx`. |
| P14 | **Cryptography** | bcrypt for passwords; `HS256` JWT with production key-strength validation (≥32 chars, rejects defaults); `secrets` for tokens/OTPs; SHA-256 only for token *storage*, not passwords. |
| P11/P27 | **Docker / config** | Multi-stage build, runs as non-root `USER user` (UID 1000), no secrets baked into layers, `DEBUG` forced `False` in prod, full security-header middleware (CSP/HSTS/nosniff/Referrer/Permissions). |
| P9 | **CORS** | Explicit origin allowlist (no `*` with credentials). |

---

## Files changed by this audit

| File | Finding | Change |
| :--- | :--- | :--- |
| `.git/config` (local) | C1 | Removed inline HF token from `space` remote |
| `backend/app/core/rate_limit.py` | H3 | Gate `x-test-client-ip` to dev/test env |
| `backend/app/main.py` | H1, H2 | Minimize anonymous `/health/db`; token-gate `/metrics` |
| `backend/app/core/config.py` | H1, H2 | Add `EXPOSE_PUBLIC_DIAGNOSTICS`, `METRICS_TOKEN` (masked) |
| `backend/app/services/otp_service.py` | M1 | Constant-time OTP compare (`hmac.compare_digest`) |
| `.env*.example` | H1, H2 | Document new hardening flags |

**Verification:** affected suites (rate limiting, 2FA, env config, security hardening, sessions, auth refresh) = **50 passed**; full backend suite re-run after changes. The H1/H2 live disclosures were re-confirmed pre-fix against the production Space.
