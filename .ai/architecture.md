# Repository Architecture & Structural Blueprint

This document outlines the architectural boundaries, repository layout, technology stack, and service topology for `idoitmyself`.

## 1. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | Docker & Docker Compose | Multi-container local environment & deployment orchestration |
| **API Backend** | Python 3.12+, FastAPI, Uvicorn | Async REST API, OpenAPI generation, AI streaming |
| **Database** | PostgreSQL | Relational persistence |
| **Cache & Queue** | Redis | Message broker & result backend for async tasks |
| **Task Worker** | Celery | Background job execution and long-running tasks |
| **AI Integration** | OpenRouter | Unified LLM routing, chat completions, streaming |
| **Frontend UI** | Vite + React + TypeScript | Fast client-side Single Page Application (SPA) |
| **Styling & Components** | Tailwind CSS + shadcn/ui | Accessible, aesthetic, high-velocity component library |

---

## 2. Service Topology (Docker Compose)

```mermaid
flowchart TD
    User["User Browser"] -->|HTTP / SSE| Web["web (Vite / Nginx)"]
    Web -->|API Requests| API["api (FastAPI)"]
    API -->|Read / Write| DB[("db (PostgreSQL)")]
    API -->|Queue Tasks| Broker[("redis (Broker / Cache)")]
    Broker --> Worker["worker (Celery)"]
    Worker -->|Read / Write| DB
    API -->|LLM Prompts / Streaming| OpenRouter["OpenRouter API"]
    Worker -->|Async AI Workloads| OpenRouter
```

---

## 3. Directory Structure

```text
.
├── .ai/                            # AI Agent knowledge base & context
│   ├── architecture.md             # System design & structural blueprint (this file)
│   ├── conventions.md              # Coding standards, style, and rules
│   └── decisions/                  # Architectural Decision Records (ADRs)
│       └── 0001-core-tech-stack...md
├── .github/workflows/              # CI/CD (GitHub Pages deployment of the landing page)
├── docs/                           # Human-facing technical & user documentation
│   ├── architecture/               # Deep-dive technical specs (data-model.md)
│   └── guides/                     # (planned) Developer guides, tutorials, onboarding
├── scripts/                        # Development, build, and automation utilities
│   └── db-init/                    # SQL run when the Postgres container is first created
├── src/                            # Application source code
│   ├── backend/                    # FastAPI application, domain logic, workers
│   │   ├── migrations/             # Alembic migrations
│   │   └── app/
│   │       ├── api/v1/             # API router and endpoints (health, sources, items, labels, ai)
│   │       ├── core/               # Settings, database setup, error types
│   │       ├── models/             # SQLAlchemy ORM models
│   │       ├── schemas/            # Pydantic request/response schemas
│   │       ├── services/           # Business logic (sources, items, labels, sync, OpenRouter client)
│   │       ├── sources/            # Source connectors (interface + registry)
│   │       └── workers/            # Celery app and task definitions
│   └── frontend/                   # Vite + React (TypeScript) SPA, currently the static landing page
│       ├── public/                 # Static assets, CNAME for the custom domain
│       └── src/
│           ├── components/         # UI components (ParticleBackground)
│           ├── components/ui/      # (planned) shadcn/ui primitives
│           ├── pages/              # (planned) Application views / routes
│           ├── lib/                # (planned) API client, utilities, hooks
│           └── types/              # (planned) TypeScript interfaces and OpenAPI types
├── tests/                          # Automated test suites
│   ├── backend/                    # Pytest unit & integration tests
│   └── frontend/                   # (planned) Vitest / React Testing Library tests
├── docker-compose.yml              # Local container orchestration
├── AGENTS.md                       # Agent operational guidelines & repository map
├── LICENSE                         # Repository license (MIT)
└── README.md                       # Project overview & quickstart
```

Entries marked *(planned)* are part of the intended layout but do not exist yet; create them when the first file that belongs there is added.

---

## 4. Component Responsibilities

### Backend (`src/backend`)
* **API Endpoints (`app/api/`)**: Thin routers validating input with Pydantic and delegating to services.
* **Domain & Services (`app/services/`)**: Business logic and orchestrators for LLM prompts, storage operations, and task dispatches.
* **AI Client (`app/services/ai_service.py`)**: OpenRouter client wrapper that streams chat completions as Server-Sent Events.
* **Database Models (`app/models/`)**: SQLAlchemy 2.0 typed models on `Base` from `app/core/database.py`. Schema changes go through Alembic migrations in `migrations/`. See [docs/architecture/data-model.md](../docs/architecture/data-model.md).
* **Schemas (`app/schemas/`)**: Pydantic models for API input/output, kept separate from ORM models.
* **Source Connectors (`app/sources/`)**: One `SourceConnector` per source type (Gmail first). Connectors only fetch and normalize data into `FetchedItem`s; `services/sync.py` persists them. See [ADR 0002](decisions/0002-generic-sources-and-items.md).
* **Labels (`services/labels.py`)**: Predefined and custom labels and their assignment to items. All label writes go through this service, which keeps the "every item has at least one label" invariant. See [ADR 0003](decisions/0003-labels.md).
* **Errors (`app/core/errors.py`)**: Services raise `AppError` subclasses (`NotFoundError`, `ConflictError`, ...), rendered as `{"error": {"code", "message"}}` by a central handler.
* **Async Workers (`app/workers/`)**: Celery tasks for heavy computation or background jobs.

### Frontend (`src/frontend`)
* **Component Layer (`src/components/ui/`, planned)**: Pure, reusable shadcn/ui primitives.
* **Feature Views (`src/pages/`, planned)**: Composite page layouts consuming domain services.
* **API Integration (`src/lib/api.ts`, planned)**: Typed HTTP client communicating with FastAPI endpoints.

---

## 5. Architectural Principles

1. **Decoupled Architecture**: Frontend and backend are completely decoupled. Communication happens strictly over typed HTTP APIs, SSE (Server-Sent Events), or WebSockets.
2. **Container-First**: Every service must be reproducible via Docker Compose without relying on ambient local machine dependencies.
3. **Strict Separation of Concerns**: Fast, synchronous requests stay on FastAPI; compute-intensive or long-running workflows offload to Celery.
4. **Decision Traceability**: Any major architectural shift or dependency addition must be logged in `.ai/decisions/`.
