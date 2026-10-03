# Coding Standards & Conventions

This document defines the coding conventions, style guides, and design patterns for `idoitmyself`.

---

## 1. General Principles

* **Keep It Simple (KISS)**: Avoid premature abstractions. Write clean, direct code first.
* **Identifier & Resource Naming (`idim-` prefix)**: Never use the full name `idoitmyself` in container names, service identifiers, database names, or internal class/code prefixes. Always use the concise `idim-` or `idim_` prefix (e.g., containers: `idim-api`, `idim-web`, `idim-db`, `idim-redis`, `idim-worker`; database: `idim_db`; celery: `idim_worker`).
* **Strict Typing Everywhere**: Python code must use complete type annotations (`typing`); Frontend must use TypeScript with strict mode enabled.
* **Documentation Parity**: Whenever changing an API contract, data model, or workflow, update the corresponding documentation and ADRs.

---

## 2. Python & FastAPI Conventions (`src/backend`)

### Style & Tooling
* **Python Version**: 3.12+
* **Linter & Formatter**: [Ruff](https://docs.astral.sh/ruff/) (replaces Black, Flake8, and isort).
* **Package Management**: `uv` or `poetry` (pinned dependencies via lockfiles).

### Code Organization & Patterns
* **FastAPI Routers**: Keep routers thin. Validate input schemas with Pydantic v2 and delegate business logic to service functions/classes in `app/services/`.
* **Async by Default**: Use `async def` for I/O-bound route handlers (database calls, OpenRouter API calls).
* **Environment Configuration**: Use `pydantic-settings` (`BaseSettings`) with `.env` support. Never hardcode secrets or URLs.
* **Database Access**: Use an async ORM (e.g. SQLModel or SQLAlchemy 2.0 async). Never perform synchronous database calls inside async endpoints.
* **Error Handling**: Throw typed `HTTPException` or custom application exceptions caught by centralized FastAPI exception handlers. Never return raw internal tracebacks to clients.

### Backend Testing
* **Framework**: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`.
* **Location**: `tests/backend/`.
* **Mocking**: Mock external network calls (OpenRouter, third-party APIs) in unit tests using fixtures or `respx`.

---

## 3. Frontend Conventions (`src/frontend`)

### Style & Tooling
* **Toolchain**: Vite + React 18+ (TypeScript).
* **Linter & Formatter**: ESLint + Prettier.
* **Styling**: Tailwind CSS with standard utility classes.

### Component Structure
* **Primitive Components (`src/components/ui/`)**: Managed via `shadcn/ui`. Do not heavily modify standard Radix wrappers unless necessary for theme consistency.
* **Feature Components (`src/components/`)**: Composed domain-specific UI units.
* **Pages (`src/pages/`)**: Route-level container components.
* **Path Aliases**: Use `@/` mapped to `src/` (e.g., `@/components/ui/button`, `@/lib/api`).

### State & API Calls
* **Server State**: Use TanStack Query (React Query) for caching, revalidation, and loading states.
* **Client State**: Keep component-local state using React hooks (`useState`, `useReducer`); elevate to lightweight stores (e.g. Zustand) only when cross-component state is needed.
* **AI Streaming**: Use native `fetch` with `ReadableStream` or EventSource/SSE helpers for streaming tokens smoothly.

---

## 4. Git & Commit Hygiene

* **Commit Messages**: Follow Conventional Commits:
  * `feat:` new feature or endpoint
  * `fix:` bug fix
  * `refactor:` code restructuring without behavior changes
  * `docs:` documentation updates
  * `chore:` dependency upgrades, config, or tooling changes
* **Secrets**: Never commit `.env` files, API keys, or database credentials. Always provide a sanitized `.env.example`.
