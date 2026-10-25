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

Final vision as stated by the owner (2026-10-25). It replaced the earlier design, where Jev classified labels in ad hoc runs. It is built incrementally, one small piece at a time, never all at once.

1. Connect an email account (a **mailbox type**, i.e. provider). Gmail first; more types later.
2. The user defines **Filters**. A filter is a set of conditions over an email's fields (sender with regex, subject, has attachment, and more), combined with **AND / OR**.
3. A filter applies to a **scope**: whole **mailbox types** and/or **individual inboxes**, picked in one hierarchical dropdown (type → its inboxes). Inboxes show their mailbox type.
4. A filter is **live once created**, with lifecycle control: it can be made **inactive** (and active again).
5. While filters are active, **Celery beat** triggers scanning at **fixed half-hour marks (:00, :30)**. Each run scans the email received since the inbox's previous run (the last 30 minutes, or longer after downtime), and every new email is run through the active filters whose scope covers its inbox. There's **no back-fill** of older mail (owner, 2026-10-25); use an ad hoc scan for that.
6. **Every filter adds a label.** When an email passes a filter, that label is applied. **Labels are just unique names**, nothing else.
7. Later: **processors** on labels, triggered when emails get that label. They emit data/artifacts for analytics, alerting and so on.

This is a self-hosted app that isn't deployed anywhere: **no backward compatibility and no migrations**. Until the first release, **schema changes go straight into the single initial migration** (`alembic/versions/*_0001_initial.py`). Never add migration files. Bring the owner's running dev DB in line with a one-off SQL change, keeping it stamped at `0001`. Reset volumes (`docker compose down -v`) only with the owner's go-ahead.

**Principle: IDIM is a generic mailbox app.** Its own concepts (filters, labels, email counts, processors, analytics) are **provider-agnostic**: an IDIM label is not a Gmail label, and counts span emails from every inbox. Gmail-specific code belongs only in the connection layer (`app/mail/gmail.py`, Gmail OAuth, Connections › Inboxes). The one deliberate exception is the **filter field catalogue**: a mailbox type may own extra fields (e.g. Gmail's category), whose values its `MailSource` provides.

## Tech stack

### Backend (fixed by owner)
- **Language:** Python
- **API framework:** FastAPI
- **Task queue:** Celery (worker + **beat**)
- **Message broker:** RabbitMQ
- **Cache / store:** Redis
- **Database:** PostgreSQL

### Backend decisions (owner)
- **Data layer:** SQLAlchemy 2 **async** (asyncpg), **Alembic** migrations, Pydantic v2 schemas, pydantic-settings for config. Python 3.12, managed with **uv**.
- **Users:** **single-user, no login.** There is no user table; inboxes belong to the instance.
- **OAuth tokens:** encrypted at rest with **Fernet**; the key is `TOKEN_ENCRYPTION_KEY` in `.env`.
- **Gmail OAuth UX:** **full-page redirect** (not a popup). The callback redirects back to the frontend.
- **Inbox tags:** a **shared `tags` table** with a many-to-many link to inboxes (tags are reusable).
- **Filters (2026-10-25):**
  - A filter has a name, an optional description, a **scope**, **one label** it adds (required), a **rule**, and a status of **active / inactive**. New filters start **active**.
  - **Scope (owner, 2026-10-25):** any mix of whole **mailbox types** and **individual inboxes**, with at least one entry.
    - A selected type covers **every inbox of that type, including ones connected later**.
    - Inboxes are covered only if picked by name. An inbox whose type is selected is dropped as redundant.
    - **Types may be mixed** in one filter. The rule may then only use fields that **every covered type** has: common fields always, a provider's own fields only when all covered types are that provider.
    - The scope is **editable**. A new scope or rule is re-checked against that constraint (422 if it fails). New filters default to all inboxes of the first type (all Gmail).
  - **Filters apply to new emails only.** A filter that is created, edited or activated runs against emails scanned from then on. Nothing is re-applied to emails already stored.
  - **Filters only ever add labels.** Labels already applied stay, whatever happens to the filter later (edit, deactivate, delete).
  - Several filters may add the same label. Each `email_labels` row records the **first filter** (in creation order) that added it, plus the scan.
- **Rule format (owner, 2026-10-25):** `{type: "group", items: [...]}`. The items are conditions and groups.
  - **Every item after the first has its own `join: "and" | "or"`** to the item before it; the first has none (422 otherwise).
  - **AND binds tighter than OR**, like SQL: `A OR B AND C` is `A OR (B AND C)`. Evaluation splits each list at every OR into runs of ANDs (`evaluate._chain`).
  - **Groups are brackets**, e.g. `(A OR B) AND (C OR D)`. They hold conditions only, with their own joins, so a rule is **at most two levels** deep.
  - Negation lives in the operators. The rule is stored as JSONB and validated by `app/filters/rule.py`.
  - The editor shows an **AND | OR toggle between every pair of items**. A new item takes the join of the last one, so a run of ORs stays ORs. Filter rows have an **Edit** button (pencil), and clicking the row also opens the editor.
- **Conditions:** `field`, `op`, `value`, optional `argument` (e.g. the header name) and `case_sensitive` (default false). Fields and operators are defined in code (`app/filters/fields.py`) and served by `GET /api/v1/filters/fields`.
  - **Common fields:** sender address, name and domain; to, cc, any recipient; reply-to; subject; body; has attachments; attachment name, type and count; size; is a reply; is from a mailing list; list id; any header.
  - **Gmail-only fields:** category, Gmail label names, important, starred. These are **as they were at scan time**.
  - **Operators:**
    - text: is, is not, contains, does not contain, starts with, ends with, matches regex, does not match regex, is empty, is not empty
    - bool: is true, is false
    - number: `=`, `≠`, `>`, `≥`, `<`, `≤`
    - enum: is, is not, is any of
  - For **list fields** (recipients, attachments, Gmail labels), a positive operator holds if **any** value matches, and its negation holds if **none** does.
  - **Regexes** use Python `re` with search semantics. They're validated when the filter is saved: an invalid one returns 422.
- **Labels (2026-10-25):** global and provider-agnostic. Each has a **display name**, which is editable and shown everywhere in the UI, a **normalised name**, which is unique and immutable, and a **colour** from a fixed palette (`gray, red, orange, amber, green, teal, blue, violet, pink`; default gray; editable). The normalised name is lowercase, with every run of non-letters/digits turned into one `_` and leading/trailing `_` trimmed: "Credit Card-Bill!" becomes `credit_card_bill`. Both names are shown on the label's detail page and edit dialog. A label can be **deleted only when no filter (active or inactive) writes it** (409 otherwise). Deleting it removes it from every email.
- **Scanning (2026-10-25):**
  - **Celery beat** fires `scans.tick` on a crontab at **fixed boundaries**, every `SCAN_INTERVAL_MINUTES` from the hour (30 → :00 and :30 UTC, which is also :00/:30 in IST). The interval must divide 60.
  - The tick queues one **scheduled** scan per inbox **covered by at least one active filter**, unless that inbox's scheduled scan is still in flight (its next window then catches up).
  - **Window:** emails received in `[inbox_sync.scanned_until, boundary)`. The first time, that's `[boundary − interval, boundary)`. Windows join up, so nothing is missed or read twice, and after downtime the next window spans the gap.
  - Discovery waits `SETTLE_SECONDS` (60) after the boundary, so mail received just before it is in Gmail's index. Listing uses Gmail search `after:`/`before:` on the received time.
  - **There's no initial back-fill and no history cursor** (both removed 2026-10-25).
  - **Email storage:** metadata for every scanned email (matched or not) is stored. Bodies are never stored.
- **Ad hoc scans (owner, 2026-10-25):** Scans › **New scan** asks for **active filters only** (one or more) and a **past date range** (inclusive local dates; an end in the future is clipped to now).
  - **One scan per inbox** covered by the chosen filters' scopes, `kind = adhoc`. Each email is checked only against the chosen filters that cover its inbox and are still active when the batch runs. If none is still active, the scan fails.
  - **Only emails no scan has stored yet** are read: stored emails are skipped, as in every scan.
  - **Clipping:** each inbox's ad hoc range is **clipped to end where scheduled scans take over**. That's `scheduled_from`: the inbox's `scanned_until`, or the current boundary if it has none yet, or earlier if a scheduled scan is still in flight. An ad hoc scan never stores mail first that every active filter should see, and it loses nothing, because mail after that point is stored by scheduled scans and would be skipped anyway.
  - Inboxes left with an empty range get no scan. If no inbox has anything left, the API returns 422.
  - Ad hoc scans don't move `scanned_until`, and they **run alongside scheduled scans** (the tick isn't blocked by them).
- **Runtime:** **everything runs in Docker Compose** (db, rabbitmq, redis, api, worker, beat, web), defined in `docker-compose.yml` at the repo root.

### Frontend (fully delegated to the agent; the owner is a backend/infra engineer, so use frontend best practices)
- **React + TypeScript**, built with **Vite**
- **Tailwind CSS** for styling
- **shadcn/ui** (Radix primitives) for components; **lucide-react** for icons
- Design bar: elegant, beautiful, pleasing, and **consistent** — one design-token set (colors, spacing, radius, typography) used everywhere; light and dark themes; no one-off styles.

Frontend libraries are the agent's call (owner delegated). In use: `react`, `react-dom`, `react-router` (URL routing), `@tanstack/react-query` (server data), `react-hook-form` + `zod` + `@hookform/resolvers` (forms), `sonner` (toasts), `tailwindcss` + `@tailwindcss/vite`, `radix-ui`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`. Fonts (Inter, Fraunces) load from Google Fonts in `index.html`. **Backend** libraries still need the owner's approval.

## Frontend design system

Theme **"Monochrome & Graphite"** (chosen by the owner; replaces the earlier beige and blue/purple themes). Palette: Primary `#18181B`, Dark `#09090B` (text), Accent `#71717A` (muted text/icons), Background `#FAFAFA`, Surface `#FFFFFF` (cards, sidebar). Borders and muted fills are derived from the same zinc scale (`#E4E4E7`, `#F4F4F5`). Dark mode is an inverted derivation: `#09090B` background, `#18181B` surfaces, `#FAFAFA` primary.

- All tokens live in `src/frontend/src/index.css` (`:root` for light, `.dark` for dark, mapped to Tailwind with `@theme inline`).
- Use **semantic token classes only**: `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `bg-primary`, `bg-accent`, `border-border`, `bg-sidebar*`, and the status colors `destructive`, `success`, `warning`. Never use raw hex values or Tailwind palette classes (`stone-200`, etc.) in components. Label colours come from the `--label-*` tokens (light and dark variants), used through `bg-label-<colour>`.
- Typography: `font-sans` (Inter) for UI, `font-serif` (Fraunces) for the wordmark and page titles.
- Light/dark: a `dark` class on `<html>`, set by `ThemeProvider`, switched with the sun/moon `ThemeToggle`, and persisted to `localStorage` under `idim-theme`. Light is the default; dark is used only if the user chose it.
- shadcn/ui is configured in `src/frontend/components.json`. Its components go in `src/components/ui/` (including `select.tsx`, used by the rule builder). Shared form helpers (`FieldError`, `Optional`, `FormError`) are in `components/form/field.tsx`.

## Current UI (as decided by the owner)

- Left sidebar: the IDIM logo (with the "I Do It Myself" tagline) at the top, the navigation in the middle, and **only** the day/night toggle at the bottom. The toggle is a switch with a sun icon on its left and a moon icon on its right, and no text.
- **Navigation has at most two levels (owner rule: a maximum, not a requirement).** A top-level section is **either a link itself** (has `path`, no sub-sections, e.g. **Dashboard**) **or** a non-clickable heading over its sub-sections. There is never a third level. The types in `components/layout/nav-config.ts` enforce this (a union of the two shapes). A sub-section can declare an `indicator` component for live status; **Scans shows a spinner while any scan is queued or running** (`ScansActivityIndicator`).
- Current navigation (in this order): **Dashboard** (a direct link), then **Automation** › **Filters**, **Labels** and **Scans**, then **Connections** › **Inboxes** (route kept as `/connections/inbox`, because the Gmail OAuth callback returns there). `/` lands on the Dashboard.
- Routes: `/dashboard`, `/automation/filters`, `/automation/filters/new` and `/automation/filters/:filterId` (the editor), `/automation/labels`, `/automation/labels/:labelId`, `/automation/scans`, `/connections/inbox`.
- **Responsive (mandatory):** every page must work at **375px** (phone) through desktop. Below `md` (768px) the sidebar is replaced by `MobileTopBar` (logo plus a menu button that opens `SidebarContent` in a left `Sheet` drawer). Use `PageHeader` and `PageBody` for the standard responsive gutters (16px on phones, 40px from `md`). Never use fixed widths that overflow a phone. `<main>` is `relative`, so Radix's hidden native form controls can't stretch the document.
- Shared page building blocks: `PageHeader`, `PageBody`, `EmptyState`, `ErrorBanner` and **`ItemList` / `ItemRow` / `Figure`** in `components/layout/`.
- **Listing pages (Inboxes, Filters, Labels, Scans) use stacked full-width rows, not card grids (owner decision).** The look is tabular without a table, modelled on openrouter.ai/models. Each row has a title with badges, muted description lines and a small meta line on the left, right-aligned figures (value over caption), and actions. Phones stack the figures under the text. New listing pages must use `ItemList`/`ItemRow`. Use dialogs for small create flows and an `AlertDialog` to confirm destructive actions. The filter editor is a **full page**, because the rule builder needs the room.

## Public product site and demo

- `src/marketing/` is a separate static Vite site for `https://idoitmyself.online`. It is deliberately separate from the self-hosted app in `src/frontend/`.
- `/` is the product and architecture page; `/demo/` is a read-only, fully fictional and anonymised static walkthrough of the app. Its persistent top bar must make the demo status clear. It must never call the API, OAuth, or any real mailbox.
- It uses the same Monochrome & Graphite tokens and the same light/dark preference (`idim-theme`) as the app.
- `.github/workflows/deploy-pages.yml` builds `src/marketing` on pushes to `main` and deploys the artifact to GitHub Pages. `src/marketing/public/CNAME` owns the `idoitmyself.online` custom-domain setting; do not omit it from the artifact.

## Running locally

```bash
docker compose up --build        # db, rabbitmq, redis, api, worker, beat, web
```
- Web: http://localhost:5173. Vite proxies `/api` to the api service, so the browser sees a single origin. (If another local dev server holds `[::1]:5173`, use http://127.0.0.1:5173.)
- API: http://localhost:8000 (OpenAPI docs at `/docs`). Alembic migrations run on api startup (`alembic upgrade head`).
- RabbitMQ management UI: http://localhost:15672.
- The Celery **worker** consumes the `scans` queue, and **beat** publishes `scans.tick`. Neither hot-reloads, so run `docker compose restart worker beat` after backend changes. Remote control, gossip and mingle are disabled because RabbitMQ 4 rejects the transient queues they need.
- Compose reads `.env` from the repo root. The Postgres volume is `pgdata`; the older volumes `idoitmyself_postgres_data`, `idoitmyself_idim_postgres_data` and `idim_idim_postgres_data` came from earlier attempts and are deliberately not used. Do not delete them without asking.
- **Scans call Gmail for real.** Never leave test filters or test inboxes in the dev database: with an inbox connected, an active filter makes beat start real scans. Test the scan engine with a fake `MailSource`.
- Backend checks: `cd src/backend && uv run ruff check . && uv run pytest`. Frontend checks: `cd src/frontend && npx tsc -b && npm run lint`.

## Features built

### Gmail inbox connection (OAuth 2.0, authorization code + PKCE)
1. The Add Inbox dialog (provider, name, tags, notes) calls `POST /api/v1/email/gmail/authorize`. The draft and PKCE verifier are stored in Redis under a one-time `state` (10-minute TTL), and the response is Google's consent URL.
2. The browser does a full-page redirect to Google. Google calls back `GET /api/v1/email/gmail/callback` (this must match `GOOGLE_REDIRECT_URI` and the Google Cloud console).
3. The callback exchanges the code, requires the `gmail.readonly` scope and a refresh token, and reads the account email from OIDC userinfo. It then creates the inbox, or updates it if that Gmail address is already connected.
4. Finally it redirects to `{FRONTEND_URL}/connections/inbox?oauth=connected|reconnected|error&reason=...`, and the page shows a toast.
- Scopes: `openid email https://www.googleapis.com/auth/gmail.readonly`.
- Tables: `inboxes` (unique on provider + email_address; `provider` is the mailbox type), `inbox_credentials` (Fernet-encrypted tokens, 1:1 with an inbox), `tags` (unique on `lower(name)`), and `inbox_tags`.
- `GET /api/v1/email/inboxes` also returns `active_filters` (active filters whose scope covers the inbox), `scanned_until` (end of the last scheduled window) and `last_scan`. The Inboxes page shows the mailbox type badge, active filters and scan state. Other endpoints: `GET /api/v1/tags`, `GET /api/v1/health`.

### Filters (Automation › Filters)
- Table `filters`: `name`, `description`, `label_id` (FK, **ON DELETE RESTRICT**), `rule` (JSONB), `status` (`active|inactive`) and `status_changed_at`.
- Scope tables: `filter_mailbox_types` (filter_id, mailbox_type) and `filter_inboxes` (filter_id, inbox_id; cascades when the inbox is deleted). `Filter.covers(inbox)` checks the scope, and `services/filters.active_filters_for(inbox)` returns the active filters for an inbox, oldest first.
- `GET /api/v1/filters` (each with its label, `emails_labelled` and `last_matched_at`), `GET /api/v1/filters/{id}`, `POST /api/v1/filters` with `scope: {mailbox_types, inbox_ids}` (201; 422 for an empty scope, an unknown label or inbox, a bad rule, or a field not every covered type has). `PATCH /api/v1/filters/{id}` (partial: name, description, scope, label_id, rule, status). Reads return `scope: {mailbox_types, inboxes: [{id, name, email_address, provider}]}`. `DELETE /api/v1/filters/{id}` (labels it applied stay), `GET /api/v1/filters/fields` (the catalogue).
- Code:
  - `app/filters/fields.py`: field catalogue and operators.
  - `app/filters/rule.py`: Pydantic rule model and validation.
  - `app/filters/evaluate.py`: a pure evaluator. `compile_rule` precompiles regexes once per batch.
  - `app/services/filters.py`: the filters service.
- Frontend (`features/filters/`):
  - **List:** one row per filter, with a status badge, scope badges ("All Gmail", inbox names), a one-line rule summary (`rule-summary.ts`) and an active switch.
  - **Scope picker:** `scope-select.tsx`, with helpers in `scope.ts`. Ticking a type selects it whole, and its inboxes show as ticked. Unticking one of those inboxes switches to the type's other inboxes, picked by name, and the type shows a partial (dash) state. In the rule builder, fields unavailable for the scope are flagged on the condition, not dropped.
  - **Editor:** a full page (`filter-editor-page.tsx`) with the rule builder (`rule-builder.tsx`, working on the draft model in `rule-draft.ts`).
  - **Labels inside the editor:** a label can be created inline from the label picker (`AddLabelDialog` with `onCreated`).
  - **Validation:** the client checks required fields and values. Regexes are checked by the server only, because Python's regex syntax differs from JavaScript's.

### Labels (Automation › Labels)
- Table `labels`: `name` (normalised, unique; also enforced by the CHECK `ck_labels_name_normalized`), `display_name` and `color` (CHECK `ck_labels_color_in_palette`). `normalize_label_name` is in `app/schemas/label.py`; the frontend mirrors it in `features/labels/name.ts` for the "Normalised as" preview only.
- **Colours in the UI:** the colour is picked with `ColorPicker` in the add and edit dialogs. It shows as a `LabelDot` (`features/labels/label-dot.tsx`) beside the label's name everywhere: label rows and page, filter rows and the label picker, email label tags, the Dashboard (by label, this month vs last, recent, needs attention) and the label filter. Every API shape that carries a label also carries its `color`. **Label colours are identity dots only, never chart series colours.**
- `GET /api/v1/labels` (each with `email_count` and the `filters` that write it), `GET /api/v1/labels/{id}`, `POST /api/v1/labels` `{display_name, color?}` (201; 409 if the normalised name is taken), `PATCH /api/v1/labels/{id}` `{display_name?, color?}`, `DELETE /api/v1/labels/{id}` (204; **409 while any filter writes it**), `GET /api/v1/labels/{id}/stats?tz`, `GET /api/v1/labels/{id}/emails?page&page_size` (newest first, with the filter that added the label).

### Scanning (Automation › Scans)
- **Tables:**
  - `scans`: inbox, `kind` (`scheduled|adhoc`), status (`queued|running|completed|failed|cancelled`), `window_start`/`window_end` (emails received in `[start, end)`), timestamps, `error`, and counters: `emails_found`, `emails_processed`, `emails_skipped` (already stored), `emails_failed`, `emails_matched`, `labels_applied`, `retries`.
  - `inbox_sync`: one row per inbox, holding `scanned_until`, the end of its last scheduled window. No row means it has never been scanned on schedule.
  - `emails`: metadata only, with the `scan_id` that stored it.
  - `email_labels`: email, label, `filter_id` (SET NULL), `scan_id`, `applied_at`.
- **Tasks on the `scans` queue** (`app/worker.py`, `app/services/scan_engine.py`):
  1. `scans.tick` (beat) → `start_due_scans(now)`: queues scheduled scans for the windows above. A queued or running scan with **no progress for `SCAN_STALE_MINUTES` (30)** is marked failed first, so a lost batch can't block its inbox forever. The boundary maths is `services/scans.schedule_boundary`.
  2. `scans.discover(scan_id)` → `discover`:
     - It lists the emails received in the scan's window.
     - For a scheduled scan, it sets the inbox's `scanned_until` to the window's end in the same transaction as `emails_found`.
     - It then publishes `scans.process` batches of `SCAN_BATCH_SIZE` (10).
  3. `scans.process(scan_id, message_ids, attempt)` → `process_batch`:
     - Emails **already stored for the inbox are skipped**, with no fetch: filters only see new mail.
     - Every other email is fetched, its metadata stored, and it's run through the **filters active at that moment whose scope covers the inbox** (for ad hoc scans, only the chosen ones among those). Matched labels are inserted, and all of this happens in one transaction.
     - Up to `SCAN_CONCURRENCY` (5) emails are in flight at once.
- **`MailSource`** (`app/mail/types.py`): `list_message_ids(start, end)` and `fetch(id)`.
  - `FetchedEmail` carries every header, `size_bytes` and `provider_fields` (the values for a provider's own filter fields).
  - Gmail (`app/mail/gmail.py`) skips drafts, spam and trash, and maps label ids to names with one `labels.list` per source.
  - Quota units: `labels.list` 1, `messages.list` 5, `messages.get` (full) 60.
- **Retries never wait in the worker (owner decision):**
  - Transient failures (Gmail 429; **403 with reason `rateLimitExceeded`/`userRateLimitExceeded`/`quotaExceeded`**; 5xx; network errors) raise `TransientError` (`app/core/retry.py`).
  - The task then **publishes the work back to RabbitMQ with a `countdown`**: exponential back-off with full jitter (`SCAN_RETRY_BASE_SECONDS` 2, capped at `SCAN_RETRY_MAX_SECONDS` 60) that honours `Retry-After`.
  - Discovery retries itself via `self.retry`. Batches publish their deferred emails as a new `scans.process` with `attempt + 1`.
  - Once a batch is throttled, its not-yet-started emails are deferred too.
  - After `SCAN_MAX_ATTEMPTS` (12) an email counts as failed. `scans.retries` counts re-queued emails.
  - The Gmail client contains **no sleeps**. The only immediate retry is one token refresh on a 401.
- **Gmail quota budget (owner decision):**
  - Google's per-user limit is **6,000 units/minute**, and Google plans to **charge for exceeding quota later in 2026**, so IDIM stays under it proactively.
  - `QuotaBudget` (`app/core/quota.py`) keeps a per-mailbox counter in **Redis**, shared by all worker processes, in 10-second windows. Each window allows `GMAIL_QUOTA_UNITS_PER_MINUTE × GMAIL_QUOTA_UTILISATION (0.9) × 10/60` units, which is 900, or 15 full fetches.
  - Every Gmail call reserves its units **before** it's made. If the window is spent, `QuotaExhausted` is raised and the work is **paced**: re-queued for the next window plus a random spread (`SCAN_PACING_SPREAD_SECONDS`, 30), **without using an attempt**.
  - Gmail calls are also capped at `GMAIL_MAX_IN_FLIGHT` (2) per worker process.
  - Celery tasks get a per-event-loop Redis client (`app.core.redis.loop_redis`).
  - Caveat: with RabbitMQ, Celery holds a delayed (ETA) message **unacked in memory** until it's due. Delays must stay well under RabbitMQ's `consumer_timeout` (30 min).
- **Completion** is atomic: `complete_scan_if_done` flips `running → completed` once `emails_processed + emails_failed >= emails_found` (after discovery).
- **Known gaps:**
  - Celery acks early, so delivery is at-most-once. `scanned_until` advances at discovery, so emails in a lost batch aren't retried by later scans. The stale check only unblocks the inbox.
  - Gmail-only fields are snapshots taken at scan time.
  - Deleted emails aren't removed.
- `GET /api/v1/scans?page&page_size&active&inbox_id` lists scans, newest first. Each scan has `window_end` and `filters`, which are set for ad hoc scans.
- `POST /api/v1/scans/{id}/cancel` stops a queued or running scan: status `cancelled`, "Stopped by the user" (409 if it already finished, 404 if unknown). Remaining batches exit without calling the provider, and batches in progress finish their current emails. Emails and labels already stored stay. A cancelled scheduled scan hands its window back (`scanned_until` returns to its `window_start`, if no later window was scanned), so the next run covers it again. Cancelled scans don't count as failures on the dashboard. In the UI, each active scan row has a **Stop** button with a confirmation dialog (`stop-scan-dialog.tsx`).
- `POST /api/v1/scans/adhoc` `{filter_ids, window_start, window_end}` creates the ad hoc scans (`services/scans.create_adhoc_scans`), publishes `scans.discover` for each, and returns them (201). Tables: `scans.window_end` and `scan_filters (scan_id, filter_id)`; `adhoc` is a value of the `scan_kind` enum.
- Frontend: `features/scans/new-scan-dialog.tsx` (filters multi-select, "Last 2/5/10 years" presets, From/To dates capped at today) and `date-range.ts`. Ad hoc rows show the range covered and the filters they run.

### Dashboard, the app-wide landing page
- Sections, top to bottom:
  1. **Filters**: date range, inbox and labels (kept in the URL).
  2. **Headline tiles**, in this order: **Emails scanned** (opens the emails window), **Active filters** (→ Filters), **Labelled** (→ Labels), **Scans completed** with emails labelled (→ Scans). The header shows "Next scan in X minutes" (`GET /api/v1/scans/schedule`) and a blinking dot when a scan is running. Every section refreshes on its own: every 5 seconds while a scan runs, otherwise every 30 (`useLiveInterval`).
  3. **Needs attention**: inboxes whose last scan failed, problem scans in the last 30 days, inboxes not scanned because no active filter covers their type, active filters that never matched, labels no active filter adds.
  4. **Trends**: emails over time; labelled emails this month vs last, per label.
  5. **Recent activity** (max 5 entries each): latest labelled emails, latest scans.
  6. **Breakdowns**: by label, by filter, top senders, by inbox.
- **Opening an email:** every email list (the Emails window, the label page, the Dashboard's recent activity) links each row to the message in its provider's web UI, in a new tab. The backend builds `open_url` with `app.mail.sources.message_url`; for Gmail that's `https://mail.google.com/mail/?authuser=<inbox address>#all/<message id>`, which picks the right signed-in account. On the frontend, `features/emails/email-link.tsx` makes the subject a link stretched over the row; other links in the row sit above it with `relative z-10`.
- **Emails window** (`features/emails/emails-explorer.tsx`): a large dialog over the stored emails. It starts from the Dashboard's filters and adds a sender/subject search, labelled / not labelled, and sorting by sent date, sender or subject. It shows stats for every match (emails, labelled, not labelled, senders, inboxes, sent-between) and a paged list with each email's labels and the filter that added them. Backed by `GET /api/v1/emails?start&end&inbox_id&label_id…&labelled&q&sort&page&page_size` (`app/services/emails.py`; the search is a literal ILIKE).
- Endpoints: `GET /api/v1/stats/overview` and `GET /api/v1/dashboard/summary` (scans by **finish time**), and `GET /api/v1/dashboard/attention|status|recent` (`app/services/dashboard.py`). All of it reads stored data only.

### Stats and exploration
- Time is each email's **sent date**; filters are **date range, inbox and labels**; each label has its own page. All stats cover **emails stored by scans** only, not the whole mailbox.
- `GET /api/v1/stats/overview?tz&start&end&inbox_id&label_id…` returns:
  - totals;
  - a zero-filled `timeline` (day up to 45 days, week up to 200, then month; buckets in the client's timezone; weeks start Monday);
  - `by_label`, `by_filter`, `by_inbox` and `top_senders` (10).
- Code: `app/services/stats.py`. A subquery that filters on labels must use an **aliased** `EmailLabel`, or SQLAlchemy auto-correlates it away.
- **Charts** (`components/charts/`: `ChartCard` with a Chart↔Table toggle, `StatTile`, `ColumnChart`, `BarList`) are plain HTML, with no chart library. They follow the dataviz rules: one neutral hue for magnitude (`--chart-emphasis`), emphasis + context grey (`--chart-context`) for labelled vs unlabelled, a hairline grid, bars ≤24px with 4px rounded tops, tooltips listing every series, and a table view for every chart.

## Repository layout (current)

```
src/
  backend/                      # FastAPI service (uv, Python 3.12)
    app/core/                   # settings, Fernet crypto, redis, retry/back-off, quota budget
    app/db/                     # declarative Base (naming convention), async session
    app/models/                 # inbox, tag, label, filter, scan (+ inbox_sync), email (+ email_labels)
    app/schemas/                # Pydantic schemas
    app/filters/                # field catalogue, rule model, evaluator (pure)
    app/mail/                   # MailSource interface + provider implementations (gmail)
    app/services/               # gmail_oauth, inboxes, tags, labels, filters, scans, scan_engine, stats, dashboard
    app/worker.py               # Celery app + beat schedule; scans.tick / scans.discover / scans.process
    app/api/v1/                 # routers (all under /api/v1)
    alembic/                    # the single initial migration (edited in place until first release)
    tests/
  frontend/                     # React / Vite app
    src/
      index.css                 # design tokens (single source of truth)
      lib/                      # api.ts (fetch wrapper, ApiError), format.ts, utils.ts (cn)
      components/ui/            # shadcn/ui primitives
      components/form/          # FieldError, Optional, FormError
      components/layout/        # AppShell, sidebar, MobileTopBar, PageHeader, PageBody, EmptyState, ErrorBanner, ItemList, nav-config.ts
      components/charts/        # ChartCard, StatTile, ColumnChart, BarList (no chart library)
      components/brand/, theme/ # Logo; ThemeProvider, ThemeToggle
      features/<feature>/       # dashboard, filters, labels, scans, inboxes, stats
      router.tsx                # routes
docs/filters-revamp-plan.md     # the reviewed plan and owner decisions for the filters revamp
docker-compose.yml              # full dev stack
.env.example                    # env var template — keep in sync when adding config
```

## Working conventions

- Never read, print, or edit `.env` / `.env.back` (real secrets). Use `.env.example` for reference and add any new variables there.
- Keep this file updated when the owner makes a decision that future sessions need to know.
