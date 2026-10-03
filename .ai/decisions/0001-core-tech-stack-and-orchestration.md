# 1. Core Technology Stack and Orchestration

Date: 2026-10-03
Status: Accepted

## Context
We needed to establish the foundational technology stack, runtime infrastructure, and frontend/backend tooling for `idoitmyself`. Key goals were rapid local development, high UI polish and performance, clean API contracts, and seamless AI model integration.

## Decision

1. **Local Orchestration & Deployment**:
   - **Docker & Docker Compose**: All services will run as containers orchestrated via Docker Compose.
   - **No Kubernetes**: Kubernetes (Kind, k3d, Minikube) was evaluated and intentionally deferred to avoid premature orchestration complexity.

2. **Backend Stack**:
   - **Language**: Python 3.12+
   - **API Framework**: FastAPI (async HTTP endpoints, Pydantic validation, automatic OpenAPI specs)
   - **Database**: PostgreSQL (primary relational data store)
   - **Background Workers**: Celery with Redis as broker/result backend (introduced as needed for async jobs)
   - **AI Provider**: OpenRouter for unified LLM routing and token streaming

3. **Frontend Stack**:
   - **Build Tool & Framework**: Vite + React with TypeScript
   - **Styling**: Tailwind CSS
   - **Component Primitives**: shadcn/ui (Radix UI primitives styled with Tailwind)
   - **Architecture**: Single Page Application (SPA). Zero server-side rendering complexity, instant Vite HMR, and decoupled consumption of the FastAPI REST/SSE endpoints.

## Consequences

- **Benefits**:
  - Fast, reproducible local setup via `docker compose up`.
  - Superior developer experience with typed API contracts (FastAPI Pydantic <-> TypeScript).
  - Modern, accessible, and fast UI out of the box with shadcn/ui.
  - Clean path for token-by-token streaming from OpenRouter through FastAPI to React via Server-Sent Events (SSE).
- **Trade-offs**:
  - Polyglot repository: Python for backend logic, TypeScript for frontend components.
  - Requires maintaining clear directory boundaries between backend and frontend code under `src/`.
