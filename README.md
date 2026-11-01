# AI Research Assistant

> A full-stack production-oriented web application using **Retrieval-Augmented Generation (RAG)**, **Large Language Models (LLM)**, and **Model Context Protocol (MCP)**.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)

---

## Overview

The AI Research Assistant is a premium research SaaS product that:

- **Grounds answers in real sources** — Retrieves relevant chunks from uploaded documents and indexed web pages
- **Leverages LLM reasoning** — Uses a large language model to synthesize retrieved context into coherent, natural answers
- **Enables tool use via MCP** — Connects the assistant to external tools, APIs, and data sources through the Model Context Protocol
- **Delivers cited, trustworthy output** — Every answer traces back to its source documents with page numbers and URLs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│               Next.js · React · TypeScript                   │
│            Tailwind CSS · shadcn/ui · Lucide                 │
│                                                              │
│  Landing · Auth · Workspace · Library · History · Settings   │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼──────────────────────────────────────┐
│                        BACKEND                               │
│                 Python · FastAPI · Pydantic                   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │   Auth   │  │   Chat   │  │   Docs   │  │     MCP     │ │
│  │ Service  │  │ Service  │  │ Service  │  │   Service   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │              │             │               │         │
│  ┌────▼──────────────▼─────────────▼───────────────▼──────┐ │
│  │              RAG Pipeline & LLM Provider               │ │
│  │   Ingest → Chunk → Embed → Store → Retrieve → Generate│ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      DATA LAYER                              │
│                                                              │
│   PostgreSQL          ChromaDB / pgvector      File Store    │
│   (Users, Chats,      (Vector embeddings,      (Uploaded     │
│    Metadata)           document chunks)         documents)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Frontend   | Next.js 14, React 18, TypeScript, Tailwind CSS    |
| UI         | shadcn/ui, Lucide icons, Radix primitives         |
| Backend    | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy    |
| Database   | PostgreSQL 15+, Alembic migrations                |
| Vectors    | ChromaDB (dev) / pgvector (prod)                  |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2)          |
| LLM        | Ollama (dev) / Configurable provider (prod)       |
| MCP        | MCP Python SDK                                    |
| Testing    | Pytest, Vitest, React Testing Library              |
| Deploy     | Docker Compose, Vercel (FE), Render (BE)          |

---

## Project Structure

```
ai-research-assistant/
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   ├── components/        # Reusable UI components
│   │   ├── lib/               # Utilities and API client
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # State management
│   │   └── types/             # TypeScript types
│   ├── public/                # Static assets
│   ├── .env.example
│   └── package.json
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── api/v1/            # Versioned API routes
│   │   ├── core/              # Config, security, deps
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── rag/               # RAG pipeline
│   │   ├── llm/               # LLM provider abstraction
│   │   ├── mcp/               # MCP tool integration
│   │   └── db/                # Database engine & session
│   ├── migrations/            # Alembic migrations
│   ├── tests/                 # Pytest test suite
│   ├── .env.example
│   └── requirements.txt
│
├── docker-compose.yml         # Local development stack
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+ and pip
- **PostgreSQL** 15+
- **Ollama** (for local LLM development)
- **Docker & Docker Compose** (recommended)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-research-assistant

# Copy environment files
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env

# Edit the .env files with your configuration

# Start all services
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL, secrets, etc.

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local

# Start the dev server
npm run dev
```

#### Ollama (Local LLM)

```bash
# Install Ollama from https://ollama.com
ollama pull llama3.1
ollama serve
```

---

## Deployment

| Service  | Platform | Guide                              |
|----------|----------|------------------------------------|
| Frontend | Vercel   | See `docs/deployment.md`           |
| Backend  | Render   | See `docs/deployment.md`           |
| Database | Managed  | Render PostgreSQL / Supabase / AWS |

---

## License

MIT License — See [LICENSE](LICENSE) for details.
