# Data Model

The backend stores data from any external source in a source-agnostic shape. Gmail is the first source; the model is designed so other sources plug in without schema changes. See [ADR 0002](../../.ai/decisions/0002-generic-sources-and-items.md) for the reasoning.

## Tables

### `sources`
A configured external data source (e.g. one Gmail account).

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `type` | varchar | `gmail` (more later); selects the connector |
| `name` | varchar(200) | Display name |
| `config` | JSONB | Connector-specific, **non-secret** settings. Returned by the API. |
| `last_synced_at` | timestamptz | Start time of the last successful sync; passed to the connector as `since` |
| `created_at`, `updated_at` | timestamptz | |

### `items`
One piece of data from a source. For Gmail, one email.

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `source_id` | UUID | FK → `sources.id`, `ON DELETE CASCADE` |
| `external_id` | varchar(255) | Id in the source system (Gmail message id). Unique per source. |
| `kind` | varchar(32) | `email` for Gmail |
| `title` | text | Email subject |
| `author` | varchar(512) | Email sender |
| `content` | text | Email body (plain text) |
| `occurred_at` | timestamptz | When the item happened at the source (email date). Indexed. |
| `data` | JSONB | Source-specific fields (thread id, recipients, provider labels, ...) |
| `created_at`, `updated_at` | timestamptz | |

## Ingestion flow

```mermaid
flowchart LR
    Provider["Provider API (e.g. Gmail)"] --> Connector["SourceConnector.fetch_items(since)"]
    Connector -->|FetchedItem| Sync["services/sync.py: sync_source"]
    Sync -->|upsert on source_id + external_id| Items[("items")]
    Sync -->|last_synced_at| Sources[("sources")]
```

1. `sync_source` looks up the connector for `source.type` in the registry.
2. The connector yields `FetchedItem`s changed since `source.last_synced_at`.
3. Each one is upserted on `(source_id, external_id)`, so re-syncing never duplicates items.
4. `last_synced_at` is set to the time the sync started and the transaction is committed.

## Adding a new source

1. Add a value to `SourceType` in `src/backend/app/models/source.py`.
2. Create a connector in `src/backend/app/sources/<name>.py`: subclass `SourceConnector`, set `source_type`, implement `fetch_items`, and decorate it with `@register_connector`.
3. Import the module in `src/backend/app/sources/__init__.py` so it registers on startup.
4. Add tests in `tests/backend/`.

## Migrations

The schema is managed with Alembic (`src/backend/migrations/`). After changing a model:

```bash
cd src/backend
alembic revision --autogenerate -m "describe the change"
# review the generated file, then
alembic upgrade head
```
