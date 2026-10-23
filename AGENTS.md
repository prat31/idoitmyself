# AGENTS.md

Guidance for AI coding agents working in this repository. Read this fully before doing anything.

## Ground rules (non-negotiable)

1. **Never commit or push.** No `git commit`, `git push`, `git stash`, `git reset`, or anything that rewrites history. The owner handles all git operations.
2. **Never change branches.** No `git checkout`/`git switch`/`git branch` to move off the current branch, and no worktrees.
3. **The owner makes all architectural decisions.** The owner is a senior software engineer and the decision-maker; the agent is the implementer.
   - Do not assume. Do not "be smart" by adding unrequested features, abstractions, libraries, patterns, or refactors.
   - If a requirement is ambiguous or a design choice is needed (data model, API shape, folder structure, new dependency, auth approach, etc.), **stop and ask** before implementing.
   - Implement exactly what was asked, nothing more.

## Product: IDIM ("I Do It Myself")

Vision as stated by the owner. It is built incrementally, one small piece at a time, never all at once.

1. Connect an email account. Gmail first; more providers later.
2. On first connect, scan the whole inbox. After that, scan periodically for changes since the last run.
3. Every email has one or more labels.
4. Label management is a feature.
5. An intelligence layer, **Jev**, categorizes and labels emails categorizes and labels emails. It does not make every decision itself: when in doubt it asks the user and learns from the answer.
6. A label may have one or more **processors**. When new emails get that label, its processors are triggered.
7. Processors emit data/artifacts, which power analytics and other features such as alerting.

**Principle: IDIM is a generic mailbox app.** Its own concepts (labels, email counts, processors, analytics) are **provider-agnostic**: an IDIM label is not a Gmail label, and counts span emails from every inbox. Gmail-specific code belongs only in the connection layer (Connections › Inbox, Gmail OAuth). That layer showing only Gmail for now is intended.

## Tech stack

### Backend (fixed by owner)
- **Language:** Python
- **API framework:** FastAPI
- **Task queue:** Celery
- **Message broker:** RabbitMQ
- **Cache / store:** Redis
- **Database:** PostgreSQL

### Backend decisions (owner, 2026-10-17)
- **Data layer:** SQLAlchemy 2 **async** (asyncpg), **Alembic** migrations, Pydantic v2 schemas, pydantic-settings for config. Python 3.12, managed with **uv**.
- **Users:** **single-user, no login.** There is no user table; inboxes belong to the instance.
- **OAuth tokens:** encrypted at rest with **Fernet**; the key is `TOKEN_ENCRYPTION_KEY` in `.env`.
- **Gmail OAuth UX:** **full-page redirect** (not a popup). The callback redirects back to the frontend.
- **Inbox tags:** a **shared `tags` table** with a many-to-many link to inboxes (tags are reusable).
- **Labels:** **global**: one shared set across all inboxes. Fields: name, optional description, a colour from a fixed palette, and an optional **filter condition** (plain-language text that later becomes the classification question for the model). **The name is immutable**; description, colour and filter condition are editable. Names are **globally unique regardless of case** and stored **normalised**: lowercase, with every run of non-letters/digits turned into a single `_` and leading/trailing `_` trimmed ("Credit Card-Bill!" becomes `credit_card_bill`). A label without a filter condition shows a warning in the list. Deleting a label removes it from all emails. `email_count` is returned as 0 until the emails table exists.
- **Jev (classification model):** TypeSafe's "System One" model on OpenRouter. It returns typed decisions with probabilities, not text. Call it at `POST https://openrouter.ai/api/alpha/decisions` with `OPENROUTER_API_KEY`; the model id is set by `JEV_MODEL` (default `typesafe/jev-1.13`). Make **one call per email**: `state` holds the email's headers, an `attachments` field (file names and MIME types, or `none`; content is never downloaded, and inline images are skipped), and a plain-text body truncated to `JEV_BODY_MAX_CHARS`, and `questions` holds one `noul` (yes/no) question per selected label, keyed by label name, built from its filter condition. The answer `answers.<label>.noul` is P(yes). Docs: https://openrouter.ai/docs/guides/community/jev and https://openrouter.ai/docs/guides/community/jev-tutorial.md
- **Match rule:** **per-label threshold** (`labels.match_threshold`, default 0.5, editable): apply the label when P(yes) ≥ threshold. If a run evaluates a label and the answer is below threshold, any existing link for that label is **removed** (the latest run wins).
- **Provenance:** each email↔label link stores Jev's **probability and the run id** that set it.
- **Email storage:** store metadata for **all scanned emails** (matched or not); bodies are never stored.
- **Skipping already-scanned work (owner decisions):** every Jev answer, yes or no, is stored per **(email, label)** in `label_evaluations`, with the probability, the run, and a **fingerprint of the filter condition** (`condition_hash`). A run asks Jev only about pairs with no current answer, and an email with nothing left to ask is skipped entirely: no Gmail fetch and no model call (`runs.emails_skipped`). **Editing a label's filter condition makes its answers stale**, so they're re-asked. **Threshold changes** are re-checked against stored probabilities only **when a run touches the email**. The New run form shows which date ranges are **already scanned** per label (`POST /api/v1/runs/coverage`) and offers **"Re-classify already scanned emails"** (`runs.reclassify`) to force re-asking.
- **Ad hoc runs (Discovery › Runs):** the form takes a required **name**, labels (a **multi-select dropdown**, nothing selected by default, at least one required; only labels **with a filter condition** can be picked), a **date range** (inclusive, in the user's local timezone, with presets), and inboxes (all preselected). Submitting creates a `runs` row and publishes a Celery task to **RabbitMQ**; a **Celery worker** fetches the emails, calls Jev and applies labels. The Runs page lists **all runs, of any status**, newest first.
- **Runtime:** **everything runs in Docker Compose** (db, rabbitmq, redis, api, web), defined in `docker-compose.yml` at the repo root.

### Frontend (fully delegated to the agent; the owner is a backend/infra engineer, so use frontend best practices)
- **React + TypeScript**, built with **Vite**
- **Tailwind CSS** for styling
- **shadcn/ui** (Radix primitives) for components; **lucide-react** for icons
- Design bar: elegant, beautiful, pleasing, and **consistent** — one design-token set (colors, spacing, radius, typography) used everywhere; light and dark themes; no one-off styles.

Frontend libraries are the agent's call (owner delegated). In use: `react`, `react-dom`, `react-router` (URL routing), `@tanstack/react-query` (server data), `react-hook-form` + `zod` + `@hookform/resolvers` (forms), `sonner` (toasts), `tailwindcss` + `@tailwindcss/vite`, `radix-ui`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`. Fonts (Inter, Fraunces) load from Google Fonts in `index.html`. **Backend** libraries still need the owner's approval.

## Frontend design system

Theme **"Monochrome & Graphite"** (chosen by the owner; replaces the earlier beige and blue/purple themes). Palette: Primary `#18181B`, Dark `#09090B` (text), Accent `#71717A` (muted text/icons), Background `#FAFAFA`, Surface `#FFFFFF` (cards, sidebar). Borders and muted fills are derived from the same zinc scale (`#E4E4E7`, `#F4F4F5`). Dark mode is an inverted derivation: `#09090B` background, `#18181B` surfaces, `#FAFAFA` primary.

- All tokens live in `src/frontend/src/index.css` (`:root` for light, `.dark` for dark, mapped to Tailwind with `@theme inline`).
- Use **semantic token classes only**: `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `bg-primary`, `bg-accent`, `border-border`, `bg-sidebar*`, and the status colors `destructive`, `success`, `warning`. Never use raw hex values or Tailwind palette classes (`stone-200`, etc.) in components.
- Typography: `font-sans` (Inter) for UI, `font-serif` (Fraunces) for the wordmark and page titles.
- Light/dark: a `dark` class on `<html>`, set by `ThemeProvider`, switched with the sun/moon `ThemeToggle`, and persisted to `localStorage` under `idim-theme`. Light is the default; dark is used only if the user chose it.
- shadcn/ui is configured in `src/frontend/components.json`. Its components go in `src/components/ui/`.

## Current UI (as decided by the owner)

- Left sidebar: the IDIM logo (with the "I Do It Myself" tagline) at the top, the navigation in the middle, and **only** the day/night toggle at the bottom. The toggle is a switch with a sun icon on its left and a moon icon on its right, and no text.
- **Navigation has at most two levels (owner rule: a maximum, not a requirement).** A top-level section is **either a link itself** (has `path`, no sub-sections, e.g. **Dashboard**) **or** a non-clickable heading over its sub-sections. There is never a third level. The types in `components/layout/nav-config.ts` enforce this (a union of the two shapes). A sub-section can declare an `indicator` component for live status; **Runs shows a spinner while any run is queued or running** (`RunsActivityIndicator`, which shares the polling runs query).
- Current navigation (in this order): **Dashboard** (a direct link), then **Discovery** › **Runs** and **Labels**, then **Connections** › **Inboxes** (route kept as `/connections/inbox`, because the Gmail OAuth callback returns there). `/` lands on the Dashboard (`/dashboard`). Discovery › Overview was removed and replaced by the Dashboard; `/discovery/overview` redirects there.
- Routes: `/dashboard` (Dashboard), `/discovery/labels` (Labels), `/discovery/labels/:labelId` (label detail), `/discovery/runs` (Runs), `/discovery/runs/:runId` (run detail) and `/connections/inbox` (Inboxes).
- **Responsive (mandatory):** every page must work at **375px** (phone) through desktop. Below `md` (768px) the sidebar is replaced by `MobileTopBar` (logo plus a menu button that opens `SidebarContent` in a left `Sheet` drawer). Use `PageHeader` and `PageBody` for the standard responsive gutters (16px on phones, 40px from `md`). Never use fixed widths that overflow a phone.
- Shared page building blocks: `PageHeader`, `PageBody`, `EmptyState`, `ErrorBanner` and **`ItemList` / `ItemRow` / `Figure`** in `components/layout/`.
- **Listing pages (Inboxes, Labels, Runs) use stacked full-width rows, not card grids (owner decision).** The look is tabular without a table, modelled on openrouter.ai/models. Each row has a title with badges, muted description lines and a small meta line on the left, right-aligned figures (value over caption), and actions. Phones stack the figures under the text. New listing pages must use `ItemList`/`ItemRow`. New pages should reuse these, with dialogs for create flows and an `AlertDialog` to confirm destructive actions.

## Running locally

```bash
docker compose up --build        # db, rabbitmq, redis, api, web
```
- Web: http://localhost:5173. Vite proxies `/api` to the api service, so the browser sees a single origin.
- API: http://localhost:8000 (OpenAPI docs at `/docs`). Alembic migrations run on api startup (`alembic upgrade head`).
- RabbitMQ management UI: http://localhost:15672. The Celery **worker** service consumes the `runs` queue; it does **not** hot-reload, so run `docker compose restart worker` after backend changes. Remote control, gossip and mingle are disabled because RabbitMQ 4 rejects the transient queues they need.
- Compose reads `.env` from the repo root. The Postgres volume is `pgdata`; the older volumes `idoitmyself_postgres_data`, `idoitmyself_idim_postgres_data` and `idim_idim_postgres_data` came from earlier attempts and are deliberately not used. Do not delete them without asking. The old `idim-*` containers were stopped (not removed) at the owner's request.
- Backend checks: `cd src/backend && uv run ruff check . && uv run pytest`. Frontend checks: `cd src/frontend && npx tsc -b && npm run lint`.

## Features built

### Gmail inbox connection (OAuth 2.0, authorization code + PKCE)
1. The Add Inbox dialog (provider, name, tags, notes) calls `POST /api/v1/email/gmail/authorize`. The draft and PKCE verifier are stored in Redis under a one-time `state` (10-minute TTL), and the response is Google's consent URL.
2. The browser does a full-page redirect to Google. Google calls back `GET /api/v1/email/gmail/callback` (this must match `GOOGLE_REDIRECT_URI` and the Google Cloud console).
3. The callback exchanges the code, requires the `gmail.readonly` scope and a refresh token, and reads the account email from OIDC userinfo. It then creates the inbox, or updates it if that Gmail address is already connected.
4. Finally it redirects to `{FRONTEND_URL}/connections/inbox?oauth=connected|reconnected|error&reason=...`, and the page shows a toast.
- Scopes: `openid email https://www.googleapis.com/auth/gmail.readonly`.
- Tables: `inboxes` (unique on provider + email_address), `inbox_credentials` (Fernet-encrypted tokens, 1:1 with an inbox), `tags` (unique on `lower(name)`), and `inbox_tags`.
- Other endpoints: `GET /api/v1/email/inboxes`, `GET /api/v1/tags`, `GET /api/v1/health`.

### Labels (Discovery › Labels)
- Table `labels`: name (unique; normalised by `normalize_label_name` in `app/schemas/label.py`, and also enforced by the CHECK `ck_labels_name_normalized`), description, and color (CHECK against the palette `gray, red, orange, amber, green, teal, blue, violet, pink`). The frontend mirrors the normaliser in `features/labels/name.ts` for a "Saved as" preview only; the server is authoritative. Colours render through the `--label-*` tokens in `index.css`.
- Column `filter_condition` (text, nullable, max 2000 characters; blank is stored as null).
- `GET /api/v1/labels`, `POST /api/v1/labels` (201; 409 if the name is taken), `PATCH /api/v1/labels/{id}` (partial update of `description`, `color` and `filter_condition`; sending `name` or any other field returns 422), `DELETE /api/v1/labels/{id}` (204/404).
- `email_count` counts `email_labels` rows across all inboxes. Deleting a label cascades through `email_labels`.
- `match_threshold` (float, strictly between 0 and 1, default 0.5) is editable in the add and edit dialogs.

### Dashboard, the app-wide landing page
- Owner decision: an app-wide Dashboard **replaced Discovery › Overview**. It's a top-level section that is itself a link (no sub-sections). Sections, top to bottom:
  1. filters (date range, inbox, labels; in the URL);
  2. headline tiles (emails scanned, labelled %, runs completed, model spend with estimated savings);
  3. **Needs attention** (inbox scan errors, failed runs or runs with failed emails in the last 30 days, labels without a condition, stale conditions, never-run labels, likely misses just under the threshold, many answers near the threshold), each linking to its fix;
  4. **Live status** (runs in progress; per inbox: last scan, scanned back to, and Gmail quota used in the current Redis budget window);
  5. **Trends** (emails over time; labelled emails this month vs last, per label);
  6. **Breakdowns** (by label, top senders, by inbox);
  7. **Coverage** (strip per label of date ranges classified with the current condition in every inbox, so gaps are visible);
  8. **Recent activity** (latest labelled emails, latest runs);
  9. **Model spend** (over time in cents, per run, per email).
- The range-scoped sections use `GET /api/v1/stats/overview` and `GET /api/v1/dashboard/summary` (runs and spend by **run finish time**). The global sections use `GET /api/v1/dashboard/attention|status|coverage|recent` (`app/services/dashboard.py`). All of it is read-only from stored data.

### Stats and exploration (shared stats API, label detail)
- Owner decisions: time is each email's **sent date**; filters are **date range, inbox and labels**; each label has its **own page**. All stats cover **emails stored by runs** only, not the whole mailbox.
- `GET /api/v1/stats/overview?tz&start&end&inbox_id&label_id…` returns totals (emails, labelled emails, label assignments, distinct senders), a zero-filled `timeline` (granularity chosen automatically: day up to 45 days, week up to 200, else month; buckets in the client's timezone, weeks start Monday), `by_label` (every label, including zeros), `by_inbox` and `top_senders` (10). The label filter means "emails having any of these labels".
- `GET /api/v1/labels/{id}`, `GET /api/v1/labels/{id}/stats?tz` (counts, last 30 days, average probability, first/last sent, timeline, by inbox, top senders), and `GET /api/v1/labels/{id}/emails?page&page_size` (≤100, newest first, with probability, the run that set it, and the email's other labels).
- Code: `app/services/stats.py`. A subquery filtering on labels must use an **aliased** `EmailLabel`, otherwise SQLAlchemy auto-correlates it away when the outer query also selects `email_labels`.
- Frontend: `features/stats/` (stats hooks, date filter, `OverviewFilters`, timeline helpers; filters are kept in **URL search params** so views can be bookmarked), `features/dashboard/` and `features/labels/label-detail-page.tsx`. Clicking a label card opens its page (a stretched link inside the card).
- **Charts** (`components/charts/`: `ChartCard` with a Chart↔Table toggle, `StatTile`, `ColumnChart`, `BarList`) are plain HTML, with no chart library. They follow the dataviz rules: one neutral hue for magnitude (`--chart-emphasis`), emphasis + context grey (`--chart-context`) for labelled vs unlabelled, hairline grid (`--chart-grid`), bars ≤24px with 4px rounded tops and 2px segment gaps, hover/focus tooltips that list every series, and a table view for every chart. **Label colours are never used as chart series colours**: they're user-picked, fail colour-blind separation and can repeat, so they appear only as identity dots beside text.

### Skipping and coverage
- `label_evaluations(email_id, label_id) → probability, condition_hash, run_id, evaluated_at`. `condition_hash` is `sha256(filter_condition)` (`app.models.email.condition_hash`). Migration 0009 backfilled only the existing positive links; "no" answers from before it were never stored, so those pairs are asked once more on their next run.
- `process_batch` loads the stored current evaluations for the whole batch in one query (`_stored_evaluations`). It asks Jev only about the missing labels, merges in the stored probabilities, and decides all of the run's labels (so threshold changes apply). It records new evaluations and links in one transaction. A fully answered email goes through `_store_skipped` (no fetch, no model call).
- Coverage merges each label's completed runs (same condition, inbox without an error), clips them to the request window, and intersects across the selected inboxes. It also returns the count of stored emails in the window already answered for that label.

### Run detail (Discovery › Runs › a run)
- Route `/discovery/runs/:runId`; each run row opens it (stretched link). It's built only from stored data (`app/services/run_insights.py`):
  - Summary and funnel: found, skipped (answers reused), sent to the model (processed − skipped), matched (+applied/−removed), failed, retries, cost (and per email), duration (and emails per minute). Progress is live while running.
  - Per label (`GET /api/v1/runs/{id}/insights?tz`): the condition and threshold **as the run asked them**, a "condition changed since" flag, answers asked, matched, within ±0.1 of the threshold, and a 10-bucket probability histogram (shown as a labelled bar list, because the spread is very skewed). Plus per-inbox counts and a sent-date timeline of the emails this run labelled.
  - Emails (`GET /api/v1/runs/{id}/emails?tab=matched|near|not_matched|skipped&label_id&sort=probability_desc|probability_asc|sent_desc&page&page_size`): one row per (email, label) with the probability vs the run's threshold. "Skipped" means answers from another run, for the same condition, that this run reused. Tab, label, sort and page are kept in the URL.
- **Provenance caveat:** per-email detail uses `label_evaluations.run_id` / `email_labels.run_id`, which move to the latest run that re-asks the same pair. Older runs keep their totals but can lose per-email rows, and runs from before migration 0009 have totals only. **Not stored yet:** which emails failed (and why), which emails lost a label, and progress over time.

### Ad hoc runs (Discovery › Runs)
- `POST /api/v1/runs/adhoc` `{name, label_ids, inbox_ids, window_start, window_end}` (name: 1–100 characters, required, not unique): the window is the half-open range `[start, end)`, and the client converts its inclusive local dates into it. Labels must have a filter condition. This creates a `runs` row (`queued`) with snapshots in `run_labels` (name, condition, threshold) and `run_inboxes`, then publishes Celery task `runs.execute` to RabbitMQ. `GET /api/v1/runs` returns all runs, newest first; `GET /api/v1/runs/{id}` returns one.
- **Execution: two task types on the `runs` queue** (`app/worker.py`, `app/services/run_engine.py`):
  1. `runs.execute(run_id)` → `discover`: lists each inbox's messages in the window through a **`MailSource`** (`app/mail/`; Gmail is in `app/mail/gmail.py` and refreshes OAuth tokens itself), records `emails_found` and `discovered_at`, then publishes `runs.process` batches of `RUN_BATCH_SIZE` (10).
  2. `runs.process(run_id, items, attempt)` → `process_batch`: for each email (up to `RUN_CONCURRENCY` (5) at once; Gmail calls are further capped at `GMAIL_MAX_IN_FLIGHT` (2) per worker process, shared across inboxes, so 4 in total with the 2-process worker) it fetches the email, calls Jev once (`app/services/jev.py`), upserts the `emails` row (metadata only), upserts or removes the `email_labels` links (probability, run_id), and bumps the counters in `runs`/`run_labels` in the same transaction.
- **Retries never wait in the worker (owner decision).** Transient failures (Gmail 429, **403 with reason `rateLimitExceeded`/`userRateLimitExceeded`/`quotaExceeded`**, 5xx, network errors; Jev 429/5xx/network) raise `TransientError` (`app/core/retry.py`). The task then **publishes the work back to RabbitMQ with a `countdown`**: exponential back-off with full jitter (`RUN_RETRY_BASE_SECONDS` 5, capped at `RUN_RETRY_MAX_SECONDS` 600) that honours `Retry-After`. Listing retries the same task via `self.retry`; batches publish the deferred emails as a new `runs.process` with `attempt + 1`. Once a batch is throttled, its not-yet-started emails are deferred too, rather than hammering the API. After `RUN_MAX_ATTEMPTS` (12) an email counts as failed. Each email that actually hits a transient error is logged with the provider's reason (e.g. `403 (rateLimitExceeded)`). `runs.retries` counts re-queued emails. The Gmail and Jev clients contain **no sleeps**; the only immediate retry is one token refresh on a 401.
- **Gmail quota budget (owner decision):** Google's per-user limit is **6,000 quota units/minute**. `messages.get` with `format=full` costs **60 units**, so at most ~100 full fetches per minute per mailbox; `messages.list` costs 5 and `history.list` 2 ([quota reference](https://developers.google.com/workspace/gmail/api/reference/quota)). Google plans to start **charging for exceeding quota later in 2026**, so we stay under it proactively. `QuotaBudget` (`app/core/quota.py`) keeps a per-mailbox counter in **Redis** (shared by all worker processes) in 10-second windows, each allowed `GMAIL_QUOTA_UNITS_PER_MINUTE × GMAIL_QUOTA_UTILISATION (0.9) × 10/60` units (900, i.e. 15 full fetches). Every Gmail call reserves its units **before** being made. If the window is spent, `QuotaExhausted` is raised, no request goes out, and the work is **paced**: re-queued for the next window plus a random spread (`RUN_PACING_SPREAD_SECONDS`, 30), **without using an attempt**. Batch-mates that never started are paced too. Only real provider errors are "deferred" with back-off (2s base, 60s cap, per Google's "start at least 1s, then double") and count toward `RUN_MAX_ATTEMPTS` and `runs.retries`. The batch endpoint isn't used: it saves HTTP overhead but not quota. Celery tasks get a per-event-loop Redis client (`app.core.redis.loop_redis`), closed when the task ends.
  - Caveat: with RabbitMQ, Celery delivers a delayed (ETA) message to a worker, which holds it **unacked in memory** (not in a pool process) until it's due. The cap must stay well under RabbitMQ's `consumer_timeout` (30 min). If truly broker-held delays are ever needed, use RabbitMQ's delayed-message exchange or a TTL + dead-letter queue.
- **Completion** is atomic: `complete_run_if_done` flips `running → completed` once `emails_processed + emails_failed >= emails_found` (after discovery), from whichever batch finishes the last email.
- **Known gaps:** a run stays `running` if a batch message is lost (e.g. the worker is killed after taking it); there is no reaper yet. Celery acks early, so delivery is at-most-once. Runs can't be cancelled or deleted from the UI.

## Repository layout (current)

```
src/
  backend/                      # FastAPI service (uv, Python 3.12)
    app/core/                   # settings, Fernet crypto, redis client
    app/db/                     # declarative Base (naming convention), async session
    app/models/                 # SQLAlchemy models
    app/schemas/                # Pydantic schemas
    app/services/               # business logic (gmail_oauth, inboxes, tags, labels, runs, run_engine, jev, stats)
    app/mail/                   # MailSource interface + provider implementations (gmail)
    app/worker.py               # Celery app; runs.execute and runs.process tasks
    app/core/retry.py           # TransientError, back-off with jitter, Retry-After parsing
    app/core/quota.py           # QuotaBudget: per-mailbox provider quota units in Redis windows
    app/api/v1/                 # routers (all under /api/v1)
    alembic/                    # migrations
    tests/
  frontend/                     # React / Vite app; `npm run dev` → http://localhost:5173
    src/
      index.css                 # design tokens (single source of truth)
      lib/utils.ts              # cn() helper (src/lib/ is intentionally un-ignored in .gitignore)
      components/ui/            # shadcn/ui primitives
      assets/logo.svg           # copy of media/logo.svg, viewBox cropped (also public/favicon.svg)
      components/brand/         # Logo (inverted in dark mode via dark:invert)
      components/layout/        # AppShell, AppSidebar/SidebarContent, MobileTopBar, PageHeader, PageBody, EmptyState, ErrorBanner, nav-config.ts
      components/theme/         # ThemeProvider, ThemeToggle
      features/<feature>/       # feature modules (api hooks, pages, components), e.g. features/inboxes
      components/charts/        # ChartCard, StatTile, ColumnChart, BarList (no chart library)
      lib/api.ts                # fetch wrapper (ApiError)
      lib/format.ts             # number/date/cost/sender formatting
      router.tsx                # routes
docker-compose.yml              # full dev stack
.env.example                    # Env var template — keep in sync when adding config
```

Existing config in `.env.example` references: PostgreSQL, OpenRouter API key, Google OAuth (Gmail/Drive read-only), backend on `http://localhost:8000` (API prefix `/api/v1`), frontend on `http://localhost:5173`.

## Working conventions

- Never read, print, or edit `.env` / `.env.back` (real secrets). Use `.env.example` for reference and add any new variables there.
- Keep this file updated when the owner makes a decision that future sessions need to know.
