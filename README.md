---
title: AI Legal Document Intelligence Platform
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.26.0
app_file: space_app.py
pinned: false
license: mit
---

# AI Legal Document Intelligence Platform

> 🚧 **Work in Progress:** This project is currently under active development and is in the process of being built.
>
> An AI-powered platform that reads the fine print so you don't have to.

## Overview

Upload any contract, NDA, rental agreement, or service agreement as a PDF and get:
- **Plain-English Summaries** — who the parties are, what the document covers, and what it means
- **Key Clause Extraction** — payment terms, termination conditions, liability, confidentiality pulled out clearly
- **Risk Flagging** — one-sided clauses, uncapped penalties, and terms that quietly favor the other party
- **Compliance Checking** — comparison against standard legal practices to surface missing protections
- **Conversational Q&A** — ask questions in plain language and get cited, clause-referenced answers

All documents, conversations, and analyses are persistently stored, organized, and semantically searchable.

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Alembic |
| **Frontend** | React 19 (TypeScript), Vite, TailwindCSS |
| **Database** | PostgreSQL 15 (Local / Cloud Managed: Neon, Supabase) |
| **Vector Store** | ChromaDB (for semantic search & RAG) |
| **AI/LLM** | Google Gemini 2.5 / 3.5 Flash (100% Free Tier Google AI Studio) |
| **AI Orchestration** | LangChain + LangGraph (multi-agent adversarial pipeline) |
| **Auth & 2FA** | JWT + Email OTP Two-Factor Authentication (SHA-256 hashed) |
| **Security & Protection**| SlowAPI IP-based rate limiting, strict CSP with HF iframe support |
| **Containerization** | Unified Multi-Stage Docker container & Hugging Face Spaces (Port 7860) |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│         (Dashboard, Viewer, Chat, Search)            │
└───────────────────────┬─────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────┐
│                  FastAPI Backend                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Auth &   │  │ Document │  │   LangGraph AI     │ │
│  │ Sessions │  │ Service  │  │   Pipeline         │ │
│  │ (JWT+OTP)│  │ (Upload, │  │ ┌────────────────┐ │ │
│  └──────────┘  │  Parse)  │  │ │ Parser Agent   │ │ │
│                └──────────┘  │ │ Clause Agent   │ │ │
│                              │ │ Risk Agent     │ │ │
│  ┌──────────┐  ┌──────────┐  │ │ Compliance     │ │ │
│  │ History  │  │ Search   │  │ │ Q&A Agent      │ │ │
│  │ & Audit  │  │ Service  │  │ └────────────────┘ │ │
│  └──────────┘  └──────────┘  └────────────────────┘ │
└────────┬──────────────┬──────────────┬──────────────┘
         │              │              │
    PostgreSQL      ChromaDB     Google Gemini
    (Users,         (Embeddings,  (Multi-Agent LLM
     Contracts,      Semantic      Inference &
     Sessions,       Search)       Vision OCR)
     History)
```

## Project Structure

```
legal-ai-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/                 # Route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── contracts.py
│   │   ├── agents/              # LangGraph AI agents
│   │   │   └── __init__.py
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   └── __init__.py
│   │   ├── services/            # Business logic
│   │   │   └── __init__.py
│   │   └── core/                # Config, DB, security utilities
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── database.py
│   │       └── security.py
│   ├── tests/                   # Backend tests
│   │   └── __init__.py
│   ├── alembic/                 # Database migrations
│   ├── uploads/                 # Local PDF storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Docker & Docker Compose (optional)

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
cp ../.env.example ../.env   # Edit with your values
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker (Full Stack)
```bash
docker-compose up --build
```

### Deploying to Hugging Face Spaces (100% Free Tier - Gradio SDK)

The application is deployed to Hugging Face Spaces using the **100% Free Gradio SDK** (`sdk: gradio`). A unified ASGI architecture hosts:
1. **The Full React 19 SPA Platform** at `/` (built locally and tracked in `frontend/dist`).
2. **The Gradio Legal Analysis Sandbox** at `/gradio`.
3. **All FastAPI Backend Endpoints** (`/auth`, `/contracts`, `/chat`, `/history`, `/analytics`, `/docs`).
4. **Cloud Database Auto-Migrations** executed on space boot.

#### 1. Space Configuration & YAML Frontmatter
The root `README.md` includes mandatory Hugging Face Spaces configuration:
```yaml
---
title: AI Legal Document Intelligence Platform
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.26.0
app_file: space_app.py
pinned: false
license: mit
---
```

#### 2. Create Gradio Space & Connect Repository
1. Navigate to [Hugging Face Spaces](https://huggingface.co/new-space).
2. Enter Space Name (e.g. `AI-Legal-Document-Intelligence-Platform`).
3. Select **Gradio** SDK (100% Free Tier) and set visibility (Public or Private).
4. Add your Hugging Face Space as a remote and push `main`:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```

#### 3. Required Space Secrets (Settings → Variables and Secrets)
Configure the following secrets in your Hugging Face Space:

| Variable / Secret | Type | Description |
|---|---|---|
| `DATABASE_URL` | Secret | Remote PostgreSQL URI with SSL (e.g. Neon, Supabase: `postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require`) |
| `GEMINI_API_KEY` | Secret | Google AI Studio API Key powering the multi-agent legal dialectic |
| `JWT_SECRET_KEY` | Secret | Cryptographically secure 256-bit secret string (`openssl rand -hex 32`) |
| `APP_ENV` | Variable | Set to `production` |
| `ALLOW_HF_IFRAME` | Variable | Set to `true` (enables CSP `frame-ancestors` for Hugging Face web view) |

#### 4. Automated Boot & Database Verification
On space boot, `space_app.py` automatically:
- Validates cloud PostgreSQL connectivity via `DATABASE_URL`.
- Executes all Alembic database schema migrations (`alembic upgrade head`).
- Mounts the Gradio Clause Analyzer at `/gradio`.
- Serves the compiled React 19 application at `/` with SPA navigation routing.

---

## Security & Protection Architecture

- **Bank-Grade Data Privacy:** Cryptographically signed JWT tokens with active token rotation and SHA-256 hashed refresh tokens.
- **Email OTP Two-Factor Authentication:** 6-digit verification codes hashed with SHA-256 at rest, protected by 5-minute expiry limits and brute-force attempt counters.
- **Endpoint Rate Limiting (SlowAPI):** Sensitive authentication endpoints are protected against credential stuffing and enumeration:
  - `POST /auth/login`: 5 requests per minute per IP.
  - `POST /auth/2fa/login-verify`: 5 requests per minute per IP.
  - `POST /auth/2fa/resend-otp`: 3 requests per 5 minutes per IP.
  - `POST /auth/register`: 5 requests per minute per IP.
  - Reverse-proxy client IP resolution via `X-Forwarded-For` and `X-Real-IP`.
- **Hugging Face Spaces Iframe Embedding:** Custom `Content-Security-Policy: frame-ancestors 'self' https://huggingface.co https://*.huggingface.co;` enables embedding in Hugging Face web views without being blocked by clickjacking policies.
- **Auto-Logout & Session Management:** Heartbeat tracking with idle timeouts and background cleanup.
- **Immutable Audit Trail:** Append-only compliance logging tracking every authentication, upload, analysis, and Q&A action.
- **Strict Multi-Tenant Isolation:** Complete isolation across contracts, conversations, and data exports.

## License
Private — All Rights Reserved
