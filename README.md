# AI Commerce Platform

## Multi-tenant AI-powered ecommerce backend

```
Python 3.11+ | FastAPI | PostgreSQL | SQLAlchemy (async) | Redis | Celery
```

---

### Quick Start

```bash
# 1. Setup environment
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Configure
copy .env.example .env
# Edit .env with your credentials

# 3. Start services
docker-compose up -d postgres redis

# 4. Run migrations
alembic upgrade head

# 5. Start API server
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

### Architecture

See [architecture.md](docs/architecture.md) for full documentation.

```
app/
├── core/          # Config, DB, security, middleware
├── api/v1/        # HTTP routes (thin — no logic)
├── services/      # ALL business logic
├── repositories/  # ALL DB access
├── ai/            # LLM, intent, retrieval (no DB)
├── adapters/      # External APIs (Shopify, WhatsApp)
├── channels/      # Channel formatters (web/whatsapp/voice)
├── events/        # Internal event bus
├── workers/       # Celery background tasks
├── models/        # SQLAlchemy ORM
└── schemas/       # Pydantic request/response
```

### Developer Responsibilities
| Developer | Owns |
|-----------|------|
| DEV 1 — Data & Integrations | `adapters/`, `repositories/`, `models/`, `workers/` |
| DEV 2 — AI & Logic | `ai/`, `services/`, `events/` |
| DEV 3 — API & Channels | `api/`, `channels/`, `schemas/` |

### Commands
```bash
make dev      # Start dev server
make test     # Run tests
make lint     # Lint + typecheck
make migrate  # Run migrations
make up       # Docker compose up
```
