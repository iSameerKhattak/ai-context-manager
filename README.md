# ContextClaw

<p align="center">
  <img src="assets/contextclaw_logo.png" alt="ContextClaw Logo" width="400">
</p>

**AI-powered context management for development teams.** Automatically ingest GitHub repositories, chunk code with AST-level precision, store embeddings in a vector database, and enable hybrid search + RAG chat across your entire codebase.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    apps/web (Next.js 15)                  │
│           Clerk Auth · TanStack Query · shadcn/ui         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────┐
│              services/api-gateway (FastAPI)               │
│   CRUD · GitHub · Search · Chat · Memory · Agents         │
└──┬──────────────┬──────────────┬──────────────┬─────────┘
   │              │              │              │
   │   ┌──────────▼──────┐  ┌────▼──────────┐  │
   │   │ services/workers  │  │ webhook-service │  │
   │   │ repo_sync · embed │  │ GitHub events    │  │
   │   └──────────┬───────┘  └─────────────────┘  │
   │              │                               │
┌──▼──────────────▼───────────────────────────────▼──┐
│              packages/shared-py (Python)             │
│  DB · Auth · Indexer · Search · LLM · Agent · Queue  │
│  Vector (Qdrant) · Embeddings · GitHub Integration   │
└─────────────────────────────────────────────────────┘
```

## Features

- **GitHub Integration** — OAuth install flow, webhook-driven auto-indexing on push
- **AST Chunking** — tree-sitter parsers for Python, TypeScript, JavaScript, Go, Java; fallback line chunker
- **Hybrid Search** — vector search (Qdrant) + full-text search (PostgreSQL tsvector) fused with RRF
- **RAG Chat** — conversation API that searches code context and generates answers with citations
- **Agent System** — autonomous agents (repo explorer, documenter, memory extractor, architecture analyzer) with tool-use (search, read file, memory read/write)
- **Project Memory** — persistent fact extraction and storage per project
- **Eval Harness** — retrieval metrics (recall@k, precision@k, MRR, NDCG) for hybrid vs vector vs FTS comparison
- **LLM Router** — multi-provider (OpenAI + DeepSeek) with pluggable strategy

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TanStack Query, Clerk, shadcn/ui, Tailwind CSS |
| API Gateway | FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Workers | Python 3.12+, RabbitMQ consumers |
| Vector Store | Qdrant |
| Message Queue | RabbitMQ |
| Database | PostgreSQL (Aurora), SQLite for dev |
| Embeddings | OpenAI `text-embedding-3-small`, DeepSeek |
| LLM | OpenAI GPT-4o / DeepSeek V3 via router |
| Code Chunking | tree-sitter (Python, TS/JSX, Go, Java) |
| CI/CD | GitHub Actions |
| Infra | Terraform (AWS: EKS, VPC, Aurora, Redis, S3) |
| Extensions | VS Code extension, CLI, MCP server (all skeletons) |

## Project Structure

```
├── apps/web                  # Next.js 15 frontend
│   ├── app/
│   │   ├── chat/             # RAG chat with citations
│   │   ├── search/           # Hybrid search with mode toggle
│   │   ├── memory/           # Project memory facts
│   │   ├── agents/           # Agent run interface + event log
│   │   ├── projects/         # Project CRUD
│   │   ├── repositories/     # GitHub repo management
│   │   └── settings/         # Org settings
│   ├── components/           # UI components (layout, integrations)
│   ├── hooks/                # React Query hooks
│   └── lib/api/              # Typed API client
├── packages/
│   ├── shared-py/            # Python shared library
│   │   └── src/contextclaw/
│   │       ├── db/           # SQLAlchemy models + engine
│   │       ├── indexer/      # Repo clone + AST chunkers
│   │       ├── search/       # Hybrid/vector/FTS search
│   │       ├── embeddings/   # Provider implementations + router
│   │       ├── vector/       # Qdrant wrapper
│   │       ├── queue/        # RabbitMQ publisher/consumer
│   │       ├── agent/        # Runner + tools + agent types
│   │       ├── integrations/ # GitHub API client
│   │       ├── auth.py       # Clerk JWT verification
│   │       └── llm.py        # LLM router with RAG
│   ├── shared-ts/            # TypeScript shared types
│   └── ui/                   # Shared UI components
├── services/
│   ├── api-gateway/          # FastAPI with all v1 endpoints
│   ├── webhook-service/      # GitHub webhook handler
│   └── workers/              # Background workers (repo_sync, embedder)
├── extensions/
│   ├── vscode/               # VS Code extension (skeleton)
│   ├── cli/                  # CLI tool (skeleton)
│   └── mcp-server/           # MCP server (skeleton)
├── infra/terraform/aws/      # AWS infrastructure as code
├── docs/adr/                 # Architecture Decision Records
│   └── ADR-0001              # Foundation decisions
├── eval_harness.py           # Retrieval evaluation suite
└── turbo.json                # Turborepo pipeline config
```

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm 9.15+
- Python 3.12+
- PostgreSQL (or `DATABASE_URL=sqlite+aiosqlite:///...` for dev)
- Qdrant (or use cloud instance)
- RabbitMQ (optional, falls back to inline processing)

### Setup

```bash
# Install JS dependencies
pnpm install

# Set up Python venv
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e packages/shared-py
pip install -e services/api-gateway

# Configure environment
cp .env.example .env
# Edit .env with your API keys and service URLs

# Run database migrations
cd services/api-gateway
alembic upgrade head

# Start development servers
pnpm dev                  # Starts all services via Turborepo
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL or SQLite connection string |
| `OPENAI_API_KEY` | OpenAI API key for embeddings + LLM |
| `DEEPSEEK_API_KEY` | DeepSeek API key for embeddings + LLM |
| `QDRANT_URL` | Qdrant cluster URL |
| `RABBITMQ_URL` | RabbitMQ connection string |
| `CLERK_SECRET_KEY` | Clerk secret key for JWT verification |
| `GITHUB_APP_ID` | GitHub App ID for integrations |
| `GITHUB_WEBHOOK_SECRET` | Webhook HMAC secret |
| `LLM_ROUTER_POLICY` | LLM provider selection strategy |

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /v1/search` | Hybrid/vector/FTS search with RRF fusion |
| `POST /v1/chat/conversations` | Create conversation |
| `POST /v1/chat/conversations/{id}/messages` | Send message + RAG response |
| `POST /v1/agents/run` | Run an autonomous agent |
| `GET /v1/agents/sessions/{id}/events` | Stream agent progress events |
| `GET/POST/DELETE /v1/memory/facts` | Project memory CRUD |
| `GET /v1/integrations/github/install-url` | GitHub App install flow |
| `POST /v1/integrations/github/webhook` | Webhook receiver (auto-index) |

## Evaluation

```bash
python eval_harness.py eval_queries.example.json
```

Compares hybrid search vs pure vector vs pure FTS across recall@k, precision@k, MRR, and NDCG.

## License

MIT
