# idoitmyself

> Modern, fullstack, decoupled application powered by FastAPI, PostgreSQL, Celery, Redis, OpenRouter, and a Vite + React SPA.
> Published static landing page: [idoitmyself.online](https://idoitmyself.online)

---

## 🛠 Technology Stack

* **API Backend**: Python 3.12, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
* **Database**: [PostgreSQL 16](https://www.postgresql.org/)
* **Cache & Broker**: [Redis 7](https://redis.io/)
* **Background Tasks**: [Celery](https://docs.celeryq.dev/)
* **AI Provider**: [OpenRouter](https://openrouter.ai/)
* **Frontend**: [Vite](https://vite.dev/), [React 19](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [Tailwind CSS v4](https://tailwindcss.com/)
* **Local Orchestration**: Docker & Docker Compose
* **Static Hosting**: GitHub Pages with custom domain via GitHub Actions

---

## 🌐 Live Landing Page (GitHub Pages)

The project includes an elegant, dark-mode static landing page with subtle canvas particle animations indicating that the project is in progress.

* **Domain**: [idoitmyself.online](https://idoitmyself.online)
* **Automated Deployment**: Triggered on every push to `main` via [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml).
* **Configuration**: Custom domain set via `src/frontend/public/CNAME`.

---

## 🚀 Quickstart (Local Development)

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/) & Docker Compose

### 1. Environment Setup
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```
*(Optional: Add your `OPENROUTER_API_KEY` to `.env` to enable AI completions).*

### 2. Start All Services
Launch the complete stack (DB, Redis, API, Celery Worker, and Web UI):
```bash
docker compose up --build
```

### 3. Access the Applications
* **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)
* **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 📂 Project Structure

```text
.
├── .ai/                    # AI Agent knowledge base & context (ADRs, architecture, conventions)
├── .github/workflows/      # CI/CD (GitHub Pages deployment)
├── docs/                   # Technical specs and developer guides
├── scripts/                # Utility and developer automation scripts
├── src/
│   ├── backend/            # FastAPI application & Celery workers
│   └── frontend/           # Vite + React (TypeScript) SPA & static landing
├── tests/
│   ├── backend/            # Pytest test suite
│   └── frontend/           # Frontend tests
├── docker-compose.yml      # Local container orchestration
└── README.md
```

---

## 🧪 Testing & Build

### Backend
Run backend tests inside the container or locally:
```bash
docker compose run --rm api pytest
```

### Frontend
Run frontend build & linting:
```bash
cd src/frontend
npm run build
```