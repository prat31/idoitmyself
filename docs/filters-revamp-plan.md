# Filters revamp: plan for review

Status: **reviewed by the owner on 2026-10-25 and implemented.** Later owner decisions supersede parts of it (filter scopes, ad hoc scans, fixed :00/:30 scan windows with no 365-day back-fill or history cursor). AGENTS.md is the current reference. The answers in §9 override anything earlier in this doc that conflicts with them.

## 1. What changes, in one paragraph

Labels stop being model-classified categories. Instead, the user defines **Filters**: deterministic rule trees (conditions joined by AND / OR) over an email's fields. Each filter belongs to one **mailbox type** (only `gmail` for now), has a lifecycle (**active / inactive**), and **adds exactly one label** when an email matches. **Labels become just unique names.** A **Celery beat** schedule wakes every 30 minutes and scans every inbox for new mail. Each new email is stored (metadata only) and run through the active filters for its mailbox type. Jev, ad hoc runs, thresholds, probabilities, coverage and model spend all go away. The Gmail connection layer (OAuth, token refresh, `MailSource`, quota budget, retry/pacing) **stays as it is** and is only extended.

## 2. Data model (fresh schema, one new initial migration)

All 9 existing Alembic migrations are deleted and replaced by a single `0001_initial`. No data migration (owner: no backward compatibility).

| Table | Columns (main) | Notes |
|---|---|---|
| `inboxes`, `inbox_credentials`, `tags`, `inbox_tags` | unchanged | Gmail OAuth stays intact. `inboxes.provider` is the **mailbox type**. |
| `inbox_sync` (new, 1:1 with inbox) | `cursor` (Gmail `historyId`), `initial_scan_completed_at`, `last_scan_at`, `last_error` | Where incremental scanning resumes. |
| `labels` | `id`, `name` (unique, case-insensitive) | Colour, description, filter_condition and match_threshold are all **removed**. |
| `filters` (new) | `id`, `name`, `description?`, `mailbox_type` (enum, = `inbox_provider`), `label_id` (FK, required), `rule` (JSONB), `status` (`active` / `inactive`), `activated_at`, timestamps | One filter adds one label. Several filters may add the same label. |
| `emails` | as today, plus `from_name`, `reply_to`, `has_attachments`, `attachments` (JSONB: name, mime type), `size_bytes`, `is_reply`, `list_id`, `has_list_unsubscribe`, `provider_meta` (JSONB, e.g. Gmail `labelIds`/category) | Metadata for **every** scanned email, matched or not, so filters can be re-applied without calling Gmail (§5). Bodies are still never stored. |
| `email_labels` | `email_id`, `label_id`, `filter_id` (provenance, SET NULL), `scan_id`, `applied_at` | Replaces probability/run provenance. |
| `scans` (new, replaces `runs`) | `id`, `inbox_id`, `kind` (`initial` / `incremental` / `reapply`), `status`, `started_at`, `discovered_at`, `finished_at`, `error`, counters (`emails_found`, `processed`, `failed`, `matched`, `labels_applied`, `retries`) | One row per inbox per tick, for history and the live indicator. |

Removed: `runs`, `run_labels`, `run_inboxes`, `label_evaluations`.

## 3. Filter rule format (stored as JSONB, validated by Pydantic)

A rule is a group. A group holds conditions and/or sub-groups. **Depth is capped at 2** (root group plus one level of sub-groups). That is still enough for any boolean expression, e.g. `(A AND B) OR (C AND NOT D)`, and keeps the builder UI usable.

```json
{
  "match": "any",
  "items": [
    { "match": "all", "items": [
        { "field": "from_address", "op": "matches_regex", "value": "@hdfcbank\\.(com|net)$" },
        { "field": "subject", "op": "contains", "value": "statement" }
    ]},
    { "field": "has_attachments", "op": "is_true" }
  ]
}
```

`match: all` = AND, `match: any` = OR. Negation lives in the operators (`not_contains`, `not_matches_regex`, `is_false`, …), so there's no NOT node. Text comparisons are case-insensitive by default, with an optional `"case_sensitive": true` per condition. Regexes are compiled when the filter is saved (an invalid one returns 422) and use search semantics.

### 3.1 Field catalogue

The catalogue is code (`app/filters/fields.py`): each field has a type, the mailbox types it applies to, and a function that reads it from an email. The API exposes it (`GET /api/v1/filters/fields?mailbox_type=gmail`) so the builder UI is data-driven.

**Common (any mailbox type)**

| Field | Type | Source |
|---|---|---|
| `from_address` | text | address part of From |
| `from_name` | text | display name of From |
| `from_domain` | text | domain of From |
| `to` / `cc` / `any_recipient` | address list (matches if **any** address matches) | To, Cc, To+Cc+Delivered-To |
| `reply_to` | text | Reply-To |
| `subject` | text | Subject |
| `body` | text | plain-text body (**needs a full fetch, never stored**; see §5) |
| `has_attachments` | bool | named, non-inline parts |
| `attachment_name` | text (any attachment) | file names |
| `attachment_type` | text (any attachment) | MIME type, e.g. `application/pdf` |
| `attachment_count` | number | |
| `size_bytes` | number | provider size estimate |
| `is_reply` | bool | `In-Reply-To` / `References` present |
| `is_mailing_list` | bool | `List-Id` or `List-Unsubscribe` present |
| `list_id` | text | `List-Id` header |
| `header` | text, plus a header-name input | any raw header, e.g. `X-Mailer` |

**Gmail only**

| Field | Type | Notes |
|---|---|---|
| `gmail_category` | enum: primary / social / promotions / updates / forums | from `CATEGORY_*` labelIds |
| `gmail_label` | text (any label) | Gmail's own label names (needs `labels.list`, cached per scan) |
| `gmail_is_important` / `gmail_is_starred` | bool | **snapshot at scan time**; later changes in Gmail aren't seen |

### 3.2 Operators per type

- **text / address list:** `equals`, `not_equals`, `contains`, `not_contains`, `starts_with`, `ends_with`, `matches_regex`, `not_matches_regex`, `is_empty`, `is_not_empty`
- **bool:** `is_true`, `is_false`
- **number:** `eq`, `ne`, `gt`, `gte`, `lt`, `lte`
- **enum:** `is`, `is_not`, `in`

Left out on purpose (tell me if you want any): sent-date conditions, which make little sense for a live filter; and Jev/AI conditions (Q1).

### 3.3 Evaluator

`app/filters/evaluate.py`: a pure function `matches(rule, email) -> bool` over a provider-agnostic `FilterableEmail` (built from a fresh `FetchedEmail` or from a stored `emails` row). It has no I/O and is unit-tested thoroughly.

## 4. Filter lifecycle and API

- Create: `name`, `description?`, `mailbox_type` (only `gmail` selectable), `label` (pick an existing one or type a new name, created on the fly), `rule`. **New filters start active.**
- `PATCH /filters/{id}`: name, description, label, rule, status. `mailbox_type` is immutable.
- `POST /filters/{id}/activate` and `/deactivate` (or `status` in the PATCH; I'd use the PATCH).
- `DELETE /filters/{id}`.
- `POST /filters/preview` `{mailbox_type, rule}`: how many stored emails match, plus a sample. It runs locally on stored metadata and makes no Gmail calls. *(Extra; see Q9.)*
- Labels: `GET/POST /labels`, `DELETE /labels/{id}`, `GET /labels/{id}` with its emails and the filters that add it. There's nothing to edit.

## 5. Scanning (Celery beat + worker)

```
beat (every SCAN_INTERVAL_MINUTES=30)
  └─ scans.tick ── for each inbox whose mailbox type has ≥1 active filter, unless a scan is in flight
       └─ scans.discover(scan_id)
            • no cursor yet → INITIAL: read the profile historyId first (1 call), then list message ids (Q4 scope)
            • cursor        → INCREMENTAL: history.list(startHistoryId, messageAdded), 2 units/page
            • history expired (Gmail 404) → fall back to listing since last_scan_at
            • publish scans.process batches; store the new cursor once discovery succeeds
       └─ scans.process(scan_id, batch, attempt)
            fetch → upsert email metadata → evaluate the active filters for the inbox's type → add labels
```

- **Reused unchanged:** `QuotaBudget`, `TransientError` + back-off, pacing on `QuotaExhausted`, re-publishing with `countdown`, `complete_*_if_done`, the token refresh in `GmailSource`. `run_engine.py` becomes `scan_engine.py` with the same shape, minus Jev.
- **`MailSource` gains:** `current_cursor()`, `list_changed_since(cursor) -> (ids, new_cursor)`, and an optional `fetch(id, need_body)`. When no active filter uses `body`, a cheaper metadata-format fetch is used (I'll check its quota cost against Google's reference during implementation).
- **Overlap guard:** a Redis lock per inbox. If an inbox's initial scan is still going (it can take hours: ~90 full fetches/min under our budget), the next ticks skip that inbox.
- **Re-applying filters to stored emails (`kind=reapply`):** runs when a filter is created, activated, or has its rule edited. It evaluates stored `emails` rows locally, with no Gmail calls and no quota. Filters that use `body` can't be re-applied this way (see Q2).
- **docker-compose:** a new `beat` service (`celery -A app.worker beat`). The queue is renamed `runs` → `scans`. The beat schedule file goes in a container tmp path.
- **Removed config:** `OPENROUTER_API_KEY`, `JEV_*`. **New:** `SCAN_INTERVAL_MINUTES` (30). The `RUN_*` settings are renamed `SCAN_*`.

## 6. Frontend

Navigation (two levels, as before):

- **Dashboard**
- **Automation** › **Filters**, **Labels**, **Scans** (Scans keeps the live spinner indicator)
- **Connections** › **Inboxes**

Pages:

- **Filters** (`/automation/filters`): `ItemList` rows showing name, an active/inactive badge, a mailbox-type badge, "adds label X", a one-line rule summary, figures (emails labelled, last match) and an active switch. Create and edit happen on a **full page** (`/automation/filters/new`, `/:id`) rather than a dialog, because the rule builder needs room: field → operator → value rows, "+ condition", "+ group", an AND/OR toggle per group, and inline regex validation. It works at 375px, where condition rows stack.
- **Labels** (`/automation/labels`): name, email count, filters that add it, delete (with AlertDialog). The detail page lists the label's emails and which filter added each one.
- **Scans** (`/automation/scans`): every scan, newest first, with inbox, kind, status, counters and duration. No detail page for now.
- **Inboxes**: each row shows its **mailbox type** (badge) and **"N active filters"** (item 2 of your request), plus sync status: initial scan done/in progress, last scan, last error.
- **Dashboard**, trimmed down. Tiles: emails scanned, labelled %, active filters, last scan. **Needs attention**: inbox scan errors, failed scans, active filters that never matched, labels no filter adds. **Live status**: scans in flight, per-inbox quota. **Trends**: emails over time. **Breakdowns**: by label, by filter, top senders, by inbox. **Recent activity**. Coverage and model spend are removed.
- Deleted: the Runs feature (new-run dialog, coverage notice, run detail, insights), label colours, threshold and condition fields.

## 7. Backend file map

| Keep as is | Change | Add | Delete |
|---|---|---|---|
| `core/crypto`, `core/quota`, `core/retry`, `core/redis`, `services/gmail_oauth`, `api/v1/gmail`, `inboxes`, `tags`, `health` | `mail/types.py`, `mail/gmail.py` (history, cursor, header extras), `models/email.py`, `models/label.py`, `worker.py` (+beat, tasks), `services/labels.py`, `services/stats.py`, `services/dashboard.py`, `config.py`, `docker-compose.yml`, `.env.example` | `filters/fields.py`, `filters/evaluate.py`, `schemas/filter.py`, `models/filter.py`, `models/scan.py`, `services/filters.py`, `services/scan_engine.py`, `services/scans.py`, `api/v1/filters.py`, `api/v1/scans.py`, `alembic/versions/0001_initial.py` | `services/jev.py`, `services/run_engine.py`, `services/run_insights.py`, `services/runs.py`, `api/v1/runs.py`, `models/run.py`, `schemas/run.py`, the 9 old migrations, `tests/test_jev.py`, `tests/test_run_*` |

Tests: rule schema validation (depth, ops vs field types, bad regex), the evaluator (every field and operator), Gmail parsing of the new headers/labelIds, history listing and cursor fallback with fakes, and the scan engine with fakes (matching, pacing, deferral, overlap lock). Quota and retry tests stay. **No real scans or Gmail calls during development**: beat won't be started on my side.

## 8. Order of work (each step ends green: ruff + pytest / tsc + lint)

1. Schema: new models and the single initial migration. Delete runs/Jev.
2. Filter core: field catalogue, rule schema, evaluator, tests.
3. Filters and labels API.
4. Gmail `MailSource` extensions (cursor, history, metadata fetch) and parsing.
5. Scan engine, worker tasks, beat, compose service.
6. Frontend: nav, Filters list and builder, Labels, Scans, Inboxes badges.
7. Dashboard and stats rework.
8. Rewrite AGENTS.md and README for the final state.

## 9. Owner decisions (2026-10-25)

1. **Jev:** removed entirely for now.
2. **Filters apply to new emails only.** A filter that is created, edited or activated runs against emails scanned from then on. There is **no** re-applying to stored emails (no `reapply` scans).
3. **Labels already applied stay**, whatever later happens to the filter.
4. **The first scan covers the last 365 days** (`INITIAL_SCAN_DAYS`). After that, scans are incremental every 30 minutes.
5. A filter applies to **all inboxes of its mailbox type**.
6. Regexes use Python `re`, validated when the filter is saved.
7. Labels have a **display name** and a **normalised name** (lowercase snake case, unique, immutable). The UI shows the display name everywhere, and both on the label's detail and edit views.
8. A label can be deleted **only if no filter writes to it** (409 otherwise).
9. No filter preview. ("Scan now" was not asked for either, so it's left out.)
10. A fresh stack: `docker compose down -v`, and the old implementation is forgotten.
11. The navigation section is called **Automation**.
