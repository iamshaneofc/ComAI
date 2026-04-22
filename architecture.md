# 🏗️ AI Commerce Platform — Production Architecture

> **Version:** 1.0 | **Stack:** Python 3.11+ · FastAPI · PostgreSQL · SQLAlchemy (async) · Redis · Celery

---

## 📁 Full Directory Tree

```
ai-commerce-platform/          # → c:\AIEcommerce\ComAI
│
├── app/
│   ├── main.py                        # FastAPI app factory & lifespan
│   │
│   ├── core/                          # Infrastructure-level concerns
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── database.py                # Async SQLAlchemy engine + session
│   │   ├── redis.py                   # Redis client factory
│   │   ├── logging.py                 # Structured JSON logging (structlog)
│   │   ├── security.py                # JWT, password hashing, OAuth2
│   │   ├── exceptions.py              # Global exception classes
│   │   ├── middleware.py              # CORS, tenant resolver, request ID
│   │   └── dependencies.py            # FastAPI DI: get_db, get_current_user
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── router.py              # Aggregates all v1 sub-routers
│   │       ├── health.py              # GET /health, GET /ready
│   │       ├── auth.py                # Login, refresh, logout
│   │       ├── chat.py                # POST /chat (main AI endpoint)
│   │       ├── products.py            # Product CRUD + sync triggers
│   │       ├── orders.py              # Order status, history
│   │       ├── events.py              # Event ingestion endpoint
│   │       ├── stores.py              # Multi-tenant store management
│   │       └── webhooks/
│   │           ├── shopify.py         # Shopify webhook receiver
│   │           └── whatsapp.py        # WhatsApp webhook receiver
│   │
│   ├── modules/                       # Domain-driven business modules
│   │   ├── auth/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   ├── store/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   ├── product/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   ├── order/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   ├── customer/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   ├── conversation/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── repository.py
│   │   └── memory/
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── repository.py
│   │
│   ├── adapters/                      # External system connectors (I/O only)
│   │   ├── shopify/
│   │   │   ├── client.py              # Shopify Admin API HTTP client
│   │   │   ├── normalizer.py          # Raw → internal schema mapping
│   │   │   ├── webhook_parser.py      # Parse & verify webhook payloads
│   │   │   └── schemas.py             # Shopify-specific Pydantic schemas
│   │   ├── custom_website/
│   │   │   ├── client.py
│   │   │   ├── normalizer.py
│   │   │   └── schemas.py
│   │   ├── whatsapp/
│   │   │   ├── client.py              # Meta Cloud API sender
│   │   │   ├── parser.py              # Inbound message parser
│   │   │   └── templates.py           # Template message builder
│   │   └── voice/
│   │       ├── twilio_client.py
│   │       └── schemas.py
│   │
│   ├── ai/                            # AI brain — pure logic, NO DB access
│   │   ├── intent/
│   │   │   ├── classifier.py          # Intent detection (zero-shot/fine-tuned)
│   │   │   └── schemas.py
│   │   ├── retrieval/
│   │   │   ├── vector_store.py        # pgvector / Pinecone abstraction
│   │   │   ├── retriever.py           # Semantic search orchestrator
│   │   │   └── reranker.py            # Cross-encoder re-ranking
│   │   ├── ranking/
│   │   │   ├── product_ranker.py      # Score & sort product recommendations
│   │   │   └── schemas.py
│   │   ├── prompt/
│   │   │   ├── builder.py             # Prompt assembly from context
│   │   │   ├── templates/
│   │   │   │   ├── sales.j2           # Jinja2 sales prompt template
│   │   │   │   ├── support.j2         # Support prompt template
│   │   │   │   └── fallback.j2
│   │   │   └── schemas.py
│   │   ├── memory/
│   │   │   ├── extractor.py           # Extract facts from conversation
│   │   │   └── summarizer.py          # Long-term memory summarization
│   │   └── providers/
│   │       ├── base.py                # Abstract LLM provider interface
│   │       ├── openai_provider.py     # OpenAI GPT-4o implementation
│   │       ├── gemini_provider.py     # Google Gemini implementation
│   │       └── factory.py             # Provider selector by config
│   │
│   ├── services/                      # Orchestration layer (THE BRAIN)
│   │   ├── chat_service.py            # End-to-end chat orchestration
│   │   ├── product_sync_service.py    # Adapter → normalize → persist
│   │   ├── event_service.py           # Event intake & dispatch
│   │   ├── memory_service.py          # Memory read/write orchestration
│   │   ├── notification_service.py    # Multi-channel alert dispatch
│   │   ├── automation_service.py      # Trigger-based automation runner
│   │   ├── order_service.py           # Order lifecycle management
│   │   └── store_service.py           # Tenant setup & configuration
│   │
│   ├── repositories/                  # DB access ONLY — no logic
│   │   ├── base.py                    # Generic CRUD base repository
│   │   ├── product_repo.py
│   │   ├── order_repo.py
│   │   ├── customer_repo.py
│   │   ├── conversation_repo.py
│   │   ├── memory_repo.py
│   │   ├── event_repo.py
│   │   └── store_repo.py
│   │
│   ├── models/                        # SQLAlchemy ORM models
│   │   ├── base.py                    # DeclarativeBase + TimestampMixin
│   │   ├── store.py                   # Store (tenant) model
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── customer.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── memory.py
│   │   └── event.py
│   │
│   ├── schemas/                       # Pydantic v2 API schemas
│   │   ├── common.py                  # PaginatedResponse, ErrorResponse
│   │   ├── chat.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── customer.py
│   │   ├── event.py
│   │   └── store.py
│   │
│   ├── events/                        # Event system (internal pub/sub)
│   │   ├── bus.py                     # In-process event bus
│   │   ├── emitter.py                 # Typed event emitter helper
│   │   ├── types.py                   # Event type definitions (dataclasses)
│   │   └── handlers/
│   │       ├── memory_handler.py      # On chat event → update memory
│   │       ├── automation_handler.py  # On order event → trigger flows
│   │       └── analytics_handler.py   # On all events → log analytics
│   │
│   ├── channels/                      # Output formatters per channel
│   │   ├── base.py                    # Abstract channel formatter
│   │   ├── web_channel.py             # JSON response for web widget
│   │   ├── whatsapp_channel.py        # WhatsApp message formatter
│   │   └── voice_channel.py           # SSML / TTS text formatter
│   │
│   ├── workers/                       # Celery/RQ background tasks
│   │   ├── celery_app.py              # Celery app factory
│   │   ├── tasks/
│   │   │   ├── sync_products.py       # Periodic Shopify product sync
│   │   │   ├── send_notifications.py  # Async notification dispatch
│   │   │   ├── process_events.py      # Heavy event processing
│   │   │   └── memory_consolidation.py# Nightly memory summarization
│   │   └── schedules.py               # Beat schedule definitions
│   │
│   └── utils/
│       ├── text.py                    # String cleaning, truncation
│       ├── datetime_utils.py          # Timezone-aware helpers
│       ├── pagination.py              # Cursor/offset pagination builders
│       ├── slugify.py
│       ├── validators.py              # Reusable Pydantic validators
│       └── crypto.py                  # Token generation, hash helpers
│
├── migrations/
│   ├── env.py                         # Alembic async env config
│   ├── script.py.mako                 # Migration template
│   └── versions/                      # Auto-generated migration files
│
├── tests/
│   ├── conftest.py                    # Shared fixtures (DB, client, mocks)
│   ├── unit/
│   │   ├── test_chat_service.py
│   │   ├── test_product_sync.py
│   │   ├── test_ai_intent.py
│   │   └── test_memory_extractor.py
│   ├── integration/
│   │   ├── test_chat_api.py
│   │   ├── test_shopify_adapter.py
│   │   └── test_event_flow.py
│   └── fixtures/
│       ├── products.json
│       └── conversations.json
│
├── scripts/
│   ├── create_superuser.py
│   ├── seed_database.py
│   ├── sync_all_stores.py
│   └── run_migrations.sh
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## 🏛️ Layer-by-Layer Breakdown

### `app/core/` — Infrastructure Foundation

| Rule | Detail |
|------|--------|
| ✅ Allowed | Config loading, DB session factory, JWT logic, logging setup |
| ❌ Not Allowed | Business logic, DB queries, AI calls |
| Used by | Every other layer imports from here |

**Key files:**
- `config.py` — `Settings` class via `pydantic-settings`, reads `.env`
- `database.py` — `AsyncEngine`, `AsyncSession`, `get_db` dependency
- `security.py` — `create_access_token()`, `verify_password()`, OAuth2 scheme
- `middleware.py` — Extracts `X-Store-ID` header → sets tenant context per request

---

### `app/api/v1/` — HTTP Interface Layer

| Rule | Detail |
|------|--------|
| ✅ Allowed | Route definitions, request validation, calling services, response mapping |
| ❌ Not Allowed | Business logic, DB queries, AI calls, cross-module imports |
| Depends on | `services/`, `schemas/`, `core/dependencies.py` |

All routes are **thin**. Example pattern:

```python
# api/v1/chat.py
@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, service: ChatService = Depends()):
    return await service.handle(payload)
```

---

### `app/modules/` — Domain Modules

Each module is a self-contained domain slice with its own `models`, `schemas`, `service`, and `repository`. This allows future extraction into microservices with minimal refactoring.

| Module | Responsibility |
|--------|---------------|
| `auth/` | Authentication tokens, user sessions |
| `store/` | Multi-tenant store config |
| `product/` | Product catalog per store |
| `order/` | Order lifecycle |
| `customer/` | Customer profiles, segments |
| `conversation/` | Chat session management |
| `memory/` | Long-term customer memory facts |

---

### `app/adapters/` — External System Connectors

| Rule | Detail |
|------|--------|
| ✅ Allowed | HTTP calls to external APIs, raw → internal schema normalization, webhook signature verification |
| ❌ Not Allowed | Business logic, DB access, calling services |
| Depends on | `schemas/` only |

**Pattern:** Adapter fetches raw data → `.normalizer.py` converts to internal Pydantic schema → handed to `services/` layer.

---

### `app/ai/` — AI Brain

| Rule | Detail |
|------|--------|
| ✅ Allowed | LLM calls, vector search, intent classification, prompt building, memory extraction |
| ❌ Not Allowed | **Direct DB access**, business decisions, API responses |
| Depends on | `core/config`, external AI SDKs only |
| Called by | `services/` layer exclusively |

The AI layer is **stateless** — all context is passed in, all results are returned. No implicit state.

---

### `app/services/` — Orchestration Layer (**Most Important**)

This is where **all business logic lives**. Services orchestrate across AI, repositories, adapters, and events.

| Rule | Detail |
|------|--------|
| ✅ Allowed | Business rules, calling repos, calling AI layer, emitting events, calling adapters' normalized output |
| ❌ Not Allowed | Direct SQL queries, direct HTTP to external APIs, formatting channel output |

**`chat_service.py` is the crown jewel** — it wires together intent detection, memory retrieval, prompt building, LLM generation, and response formatting.

---

### `app/repositories/` — Data Access Layer

| Rule | Detail |
|------|--------|
| ✅ Allowed | SQLAlchemy queries, inserts, updates, deletes |
| ❌ Not Allowed | Business logic, AI calls, HTTP requests |
| Depends on | `models/`, `core/database.py` |

```python
# repositories/product_repo.py
class ProductRepository:
    async def get_by_store(self, store_id: UUID, limit: int) -> list[Product]:
        ...
```

`store_id` is a **mandatory parameter** on every repository method (multi-tenancy enforcement).

---

### `app/events/` — Internal Event System

Decouples side-effects from primary flows. After a chat completes, the service emits a `ChatCompletedEvent` — handlers independently update memory, trigger automations, and log analytics **without blocking the response**.

---

### `app/channels/` — Output Formatters

Converts a unified `AIResponse` object to the format required by each channel:

| Channel | Output Format |
|---------|--------------|
| `web_channel` | JSON with markdown text |
| `whatsapp_channel` | WhatsApp interactive message payload |
| `voice_channel` | SSML-tagged speech text |

---

## 🔁 Data Flow Diagrams

### 1. Chat Request Flow

```
User Message (any channel)
        │
        ▼
[Channel Adapter / Webhook]  ← Parses raw payload to internal schema
        │
        ▼
[API: POST /v1/chat]  ← Validation only (Pydantic)
        │
        ▼
[ChatService]  ← ALL business logic lives here
   ├── MemoryService.get_context(customer_id, store_id)
   │       └── MemoryRepository.fetch_facts()
   ├── AI.intent.classifier.detect(message)
   ├── AI.retrieval.retriever.search(query, store_id)
   ├── AI.prompt.builder.build(intent, context, products)
   ├── AI.providers.openai.generate(prompt)
   ├── MemoryService.update(new_facts_extracted)
   ├── EventBus.emit(ChatCompletedEvent)
   └── ChannelFormatter.format(response, channel="web")
        │
        ▼
[API Response]  ← Thin wrapper, no logic
```

---

### 2. Product Sync Flow

```
[Shopify Webhook / Periodic Task]
        │
        ▼
[Adapters: shopify.client.py]  ← Raw Shopify API response
        │
        ▼
[Adapters: shopify.normalizer.py]  ← Maps to internal ProductSchema
        │
        ▼
[ProductSyncService]  ← Business rules: dedup, upsert logic, tagging
        │
        ▼
[ProductRepository.upsert(store_id, product)]  ← DB write
        │
        ▼
[EventBus.emit(ProductSyncedEvent)]  ← Triggers re-indexing for vector search
```

---

### 3. Event Capture Flow

```
[API: POST /v1/events]  ← e.g. page_view, add_to_cart
        │
        ▼
[EventService.ingest(event, store_id)]
   ├── EventRepository.save(event)
   ├── EventBus.emit(UserBehaviorEvent)
        │
        ▼
[Handlers fire concurrently]
   ├── MemoryHandler  → Updates customer interest profile
   ├── AutomationHandler  → Checks trigger rules, queues WhatsApp flow
   └── AnalyticsHandler  → Writes to analytics aggregation table
```

---

## 👨‍💻 Developer Responsibilities

### DEV 1 — Data & Integrations

**Owns:**
- `app/adapters/` — All external connectors
- `app/repositories/` — All database queries
- `app/models/` — SQLAlchemy models
- `app/workers/` — Background sync tasks
- `migrations/` — Alembic migrations
- `scripts/` — Operational scripts

**Must NOT touch:**
- `app/ai/` — No AI layer changes
- `app/api/` — No route definitions
- `app/services/` — No business logic

---

### DEV 2 — AI & Business Logic

**Owns:**
- `app/ai/` — Full AI brain
- `app/services/` — All orchestration services
- `app/events/` — Event system and handlers
- `app/modules/*/service.py` — Module-level service logic

**Must NOT touch:**
- `app/api/` — No route handlers
- `app/repositories/` — No raw queries
- `app/adapters/` — No external API clients

---

### DEV 3 — API & Channels

**Owns:**
- `app/api/` — All route definitions and versioning
- `app/channels/` — Output formatters
- `app/schemas/` — All Pydantic request/response schemas
- `app/core/middleware.py` — Request pipeline
- `tests/integration/` — API-level integration tests

**Must NOT touch:**
- `app/ai/` — No AI logic
- `app/services/` — No orchestration (only consumes)
- `app/models/` — No ORM model changes

---

## ⚙️ Development Setup

### 1. Clone & Environment

```bash
# Navigate to project
cd c:\AIEcommerce\ComAI

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/Mac
# Edit .env with your values
```

### 3. Database Setup

```bash
# Start services
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Optional: seed data
python scripts/seed_database.py
```

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run Background Workers

```bash
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info  # Scheduler
```

### 6. Makefile Shortcuts

```bash
make dev        # Start FastAPI dev server
make worker     # Start Celery worker
make migrate    # Run alembic upgrade head
make test       # Run pytest
make lint       # Run ruff + mypy
```

---

## 🧠 Design Philosophy

| Principle | How it's Applied |
|-----------|-----------------|
| **Clean Architecture** | Dependencies point inward: API → Services → Repos → DB |
| **Domain-Driven Design** | Each `module/` is a bounded context with its own models/schemas/services |
| **Multi-tenancy first** | `store_id: UUID` is required on every service method and repo query |
| **Scalability path** | Each `module/` can become a microservice — just add a FastAPI app + its own DB |
| **Testability** | Services depend on repo interfaces, easily mocked; AI layer is pure functions |
| **Observability** | Structured JSON logging in every service layer; request IDs tracked end-to-end |
