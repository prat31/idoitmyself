# 2. Generic Sources, Items and Connectors

Date: 2026-10-16
Status: Accepted

## Context
The first data source is Gmail, but more sources will follow. If the schema and services were built around email, every new source would need its own tables, endpoints and labelling logic.

## Decision

1. **`sources` table**: one row per configured account/feed. `type` (e.g. `gmail`) selects the connector; `config` (JSONB) holds connector-specific, non-secret settings; `last_synced_at` is the incremental sync cursor.
2. **`items` table**: one row per piece of data, whatever the source. Fields every source can fill are columns (`kind`, `title`, `author`, `content`, `occurred_at`); anything source-specific goes in `data` (JSONB). For Gmail: `kind = "email"`, `title` = subject, `author` = sender, `data` = thread id, recipients, provider labels.
3. **Deduplication**: `(source_id, external_id)` is unique. Ingestion upserts on it, so re-syncing is idempotent.
4. **Connectors** (`app/sources/`): a connector subclasses `SourceConnector`, yields `FetchedItem`s from `fetch_items(since)` and registers itself with `@register_connector`. Connectors never touch the database; `app/services/sync.py` persists what they yield.
5. **Single user**: there is no user/account model. Everything belongs to the one owner of the deployment.
6. **Migrations**: Alembic owns the schema (`src/backend/migrations/`). The API container runs `alembic upgrade head` on start. Enums are stored as VARCHAR rather than native Postgres enums so adding a value needs no type migration.

## Consequences

- Adding a source = one connector class + one `SourceType` value; no new tables or endpoints.
- Source-specific querying (e.g. by Gmail thread) goes through JSONB until it proves common enough to promote to a column.
- Adding multi-user support later means adding an owner column to `sources` (and custom labels) plus a data migration.
- Secrets such as OAuth tokens must not go in `sources.config`, which the API returns. They need separate storage when the Gmail connector is built.
