<p align="center"><img src="media/logo.svg" alt="IDIM" width="120"></p>

# IDIM — I Do It Myself

A self-hosted mailbox app. Connect your inbox, define labels in plain language, and let **Jev** (a classification model) label your emails.

## Features

- **Inboxes**: connect Gmail with OAuth (read-only). Tokens are encrypted at rest.
- **Labels**: one shared set across all inboxes. Each label has a plain-language filter condition and a match threshold.
- **Runs**: classify emails in a date range. Jev is asked one yes/no question per label, and answers it already gave are reused.
- **Dashboard**: stats, trends, coverage, model spend, and things that need attention.

## Stack

| Layer | Tech |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic |
| Jobs | Celery workers, RabbitMQ |
| Storage | PostgreSQL, Redis |
| Web | React, TypeScript, Vite, Tailwind, shadcn/ui |
| Model | Jev on OpenRouter |

## Quick start

Requires Docker.

1. Copy the env template and fill it in:

   ```bash
   cp .env.example .env
   ```

   | Variable | Where to get it |
   |---|---|
   | `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) |
   | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | A Google Cloud OAuth client with the Gmail API enabled. Add `GOOGLE_REDIRECT_URI` as an authorised redirect URI. |
   | `TOKEN_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

2. Start everything:

   ```bash
   docker compose up --build
   ```

| Service | URL |
|---|---|
| Web app | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| RabbitMQ UI | http://localhost:15672 |

Migrations run automatically when the API starts. The worker doesn't hot-reload, so run `docker compose restart worker` after backend changes.

## Development checks

```bash
cd src/backend && uv run ruff check . && uv run pytest
cd src/frontend && npx tsc -b && npm run lint
```

## Project layout

```
src/backend/    FastAPI app, Celery worker, migrations, tests
src/frontend/   React app
media/          Logo
```

See [AGENTS.md](AGENTS.md) for design decisions and architecture details.

## License

[MIT](LICENSE)
