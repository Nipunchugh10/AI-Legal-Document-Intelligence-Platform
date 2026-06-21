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
| **Frontend** | React 18+ (TypeScript), Vite |
| **Database** | PostgreSQL 15 |
| **Vector Store** | ChromaDB (for semantic search & RAG) |
| **AI/LLM** | Z.AI GLM-4.7-Flash (free cloud API) |
| **AI Orchestration** | LangChain + LangGraph (multi-agent pipeline) |
| **Auth** | JWT + SMS OTP Two-Factor Authentication (Indian +91 numbers) |
| **Containerization** | Docker + Docker Compose |

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
    PostgreSQL      ChromaDB      Z.AI API
    (Users,         (Embeddings,  (LLM Inference)
     Contracts,      Semantic
     Sessions,       Search)
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

## Security
- JWT-based authentication with server-side session management
- SMS OTP Two-Factor Authentication (Indian +91 numbers at launch)
- Automatic session expiry and idle timeout
- Complete audit trail of all user actions
- Strict data isolation — each user's documents are fully separated

## License
Private — All Rights Reserved
