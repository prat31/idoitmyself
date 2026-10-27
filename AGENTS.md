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
5. While filters are active, **Celery beat** triggers scanning at **fixed boundaries of the scan interval** (owner, 2026-10-25: every 30 minutes, 1 hour, 3 hours, 6 hours or daily; **default 3 hours**; set on the Scans page). Each run scans the email received since the inbox's previous run (one interval, or longer after downtime), and every new email is run through the active filters whose scope covers its inbox. There's **no back-fill** of older mail (owner, 2026-10-25); use an ad hoc scan for that.
6. **Every filter adds a label.** When an email passes a filter, that label is applied. **Labels are just unique names**, nothing else.
7. **Processors** run on labels: when an email newly gets one of a processor's labels, the processor reads it, writes **records** into **datasets**, and can ask for **actions** (notifications) or user **input**. **Dashboards** show the datasets. v1 (one label per processor, one JSON result) was replaced on 2026-10-26 by v2. The plan is `docs/processors-v2-plan.md`; what's built is under Features built › Processors.
   - **Owner decisions (2026-10-26), all in force:**
     - **Processors ↔ labels is n–n.** A processor runs **once per email**, whichever and however many of its labels the email gets. A kind may have any number of processors.
     - **Code only:** processors are **deterministic code** (no LLM extraction, no OCR), written against a small SDK. A Claude Code skill guides adding one: `.claude/skills/add-processor`.
     - **Never send sensitive data to AI:** processors never send it. Any LLM call goes through OpenRouter only. AI filter conditions are unchanged, because the user opts into them per filter.
     - **Input:** every processor receives one standard `EmailDocument`, cached **encrypted in Redis** for an hour, so processors share one fetch. Bodies and attachments are never stored permanently.
     - **Celery:** runs on their own worker service (`processor-worker`), are retryable, idempotent (a re-run replaces its records) and durable (outbox, sweep, acks_late).
     - **Deleting:** deleting a processor **keeps its records**. A label can't be deleted while a processor uses it (409).
     - **Credit cards:** the parent kind (credit card statements) picks a child parser (e.g. Yes Bank) by the **sender's domain**. Other senders are skipped.
     - **Protected PDFs:** a protected PDF asks for its password per **(sender address, label)**, through the generic input flow. The run waits as `needs_input`, and the **Home page asks for it**, with a link to the email (new tab). Saving it re-runs the waiting emails. A wrong password asks again.
     - **State across emails** (later) comes from **derived datasets**: pure functions over records, never state kept by processors.
     - **Side effects:**
       - Processors can request side effects (actions), each delivered at most once.
       - **Notifications are in-app (always) plus Telegram.** Telegram is used when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are both set, and silently skipped otherwise.
       - The in-app ones are marked read when opened or ticked, or with "Mark all read". Opening the list doesn't mark them read.
       - **A failed run** (an email a processor should handle but couldn't) also creates an **in-app notification** (owner, 2026-10-26; not Telegram). It names the processor, the email's subject and the reason, and links to the email. Skipped runs don't notify.
       - **Every notification can be dismissed** (×). It then leaves the list and counts as read.
     - **Navigation:** the old Dashboard is now **Home**. A top-level **Dashboards** section shows one dashboard per processor (from its kind's default spec). Dashboards become editable in the UI later, then can mix processors' datasets.
8. **Built-in defaults (owner, 2026-10-26; built):**
   - The first deploy ships with some **filters, labels and processors already in place**.
   - **Mechanism:**
     - The defaults are defined in code.
     - They're seeded on API startup, after the migrations.
     - Each default is applied **once**, recorded by a stable key, so it never comes back or overwrites anything.
     - Defaults added in later releases still reach existing installs.
   - **Seeded active.**
   - **Defaults can be edited and deactivated, but not deleted.** There's no "reset to default".
   - **Shown with a "Default" badge** (`components/layout/default-badge.tsx`) on rows and detail pages. Their delete buttons are hidden, and the API returns 409.
   - A missing `OPENROUTER_API_KEY` never blocks seeding (see AI conditions).
   - **Code:**
     - `app/defaults.py` holds `LABELS`, `FILTERS` and `PROCESSORS`, plus `apply_defaults`.
     - It runs as `python -m app.defaults` after `alembic upgrade head` (compose api command and Dockerfile).
     - Rows carry a unique `default_key`, and API reads expose it as `is_default`. Seeded keys are recorded in `applied_defaults`.
     - A default label whose normalised name already exists is adopted, not duplicated.
     - `tests/test_defaults.py` validates every default.
   - **Current defaults:**
     - Label **Credit card bill** (`credit_card_bill`).
     - Filter **All Banks Credit Card Bills**, all Gmail. Its rule: (sender address is `estatement@yes.bank.in` OR `statement@idfcfirst.bank.in`) AND has attachments AND sender address ends with `bank.in`.
     - Processor **Credit card bills** (`credit_card_statements`) on the Credit card bill label. It's active, so it runs on every newly labelled bill.
   - **Processors never send sensitive information to any AI.** Any LLM call goes through **OpenRouter only**.
   - AI filter conditions are unchanged, because the user opts into them per filter.

This is a self-hosted app that isn't deployed anywhere: **no backward compatibility and no migrations**. Until the first release, **schema changes go straight into the single initial migration** (`alembic/versions/*_0001_initial.py`). Never add migration files. Bring the owner's running dev DB in line with a one-off SQL change, keeping it stamped at `0001`. Reset the data (stop the stack and delete `./.data`) only with the owner's go-ahead.

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
  - **AI conditions (owner, 2026-10-25):** field `ai`, type `ai`, ops `matches` / `not_matches`. The value is a natural-language description (at most 1,000 characters), and there are **at most 5 per rule**. **Jev** decides them: it's TypeSafe's "System One" model, called through OpenRouter's Decisions API (`POST https://openrouter.ai/api/alpha/decisions`, `app/services/jev.py`).
    - **Join with anything:** an AI condition is an ordinary rule item, so it takes AND/OR joins and can sit inside groups. Every mailbox type has it.
    - **Three-valued evaluation** (`app/filters/evaluate.py`): until its answer is known, an AI condition is *unknown*. `CompiledRule.pending` returns the AI questions that could still change the result. `scan_engine.pending_questions` collects those across the candidate filters and skips filters whose label is already certain. Jev is **called only when an answer matters**, with **one request per email** holding all open questions as `noul` (yes/no) questions. Identical descriptions share a question key (`question_key`, a hash of the text).
    - The condition holds when P(yes) ≥ `JEV_THRESHOLD` (0.5, global). `not_matches` inverts that. An unanswered AI condition counts as not holding.
    - **State sent to Jev:** from, to, cc, subject, date, attachment names and types, and the plain-text body truncated to `JEV_BODY_MAX_CHARS` (8000). Nothing from Jev is stored, only the resulting labels.
    - **The key isn't needed to save (owner, 2026-10-26).** AI conditions can be saved and seeded without `OPENROUTER_API_KEY`. It's checked when a scan runs. Without it, `process_batch` **skips the candidate filters that have AI conditions**, and the other filters still run. An ad hoc scan left with no filters fails. Home's Needs attention lists those filters (`filters_skipped_without_ai_key`). `GET /filters/fields` returns `ai_enabled` (whether the key is set), and the editor shows a note when it isn't.
    - **Errors in scans:** Jev 429/5xx/network errors are transient, so the email is deferred and fetched again on retry. 401/402/403 are fatal and fail the scan. Any other Jev error fails that email.
    - **UI:** AI conditions aren't in the field dropdown. They have their own gradient card (`features/filters/ai-condition.tsx`) with a Matches / Doesn't match toggle, a textarea and example suggestions, and a **"Describe in plain English"** button at the root and in groups. The gradient uses the `--ai-1/2/3` tokens, the one deliberate colour accent, reserved for AI conditions.
  - **Operators:**
    - text: is, is not, contains, does not contain, starts with, ends with, matches regex, does not match regex, is empty, is not empty
    - bool: is true, is false
    - number: `=`, `≠`, `>`, `≥`, `<`, `≤`
    - enum: is, is not, is any of
  - For **list fields** (recipients, attachments, Gmail labels), a positive operator holds if **any** value matches, and its negation holds if **none** does.
  - **Regexes** use Python `re` with search semantics. They're validated when the filter is saved: an invalid one returns 422.
- **Labels (2026-10-25):** global and provider-agnostic. Each has a **display name**, which is editable and shown everywhere in the UI, a **normalised name**, which is unique and immutable, and a **colour** from a fixed palette (`gray, red, orange, amber, green, teal, blue, violet, pink`; default gray; editable). The normalised name is lowercase, with every run of non-letters/digits turned into one `_` and leading/trailing `_` trimmed: "Credit Card-Bill!" becomes `credit_card_bill`. Both names are shown on the label's detail page and edit dialog. A label can be **deleted only when no filter (active or inactive) writes it** (409 otherwise). Deleting it removes it from every email.
- **Scanning (2026-10-25):**
  - **Interval (owner, 2026-10-25):** stored in the database, in the single-row table `scan_settings` (`id = 1`, `interval_minutes` ∈ `SCAN_INTERVALS` = 30, 60, 180, 360, 1440; default 180, inserted by the migration). It's changed from the **dropdown at the top of the Scans page** (`scan-interval-select.tsx`) via `PUT /api/v1/scans/schedule` (422 for any other value). `GET` returns `interval_minutes`, `intervals`, `timezone` and `next_run_at`.
  - **Boundaries** fall every interval **from midnight in `SCAN_TIMEZONE`**, a deploy-time setting (IANA name, default `Asia/Kolkata`, checked at startup). With 3 hours that's 00:00, 03:00… IST; daily is midnight IST. The maths is `services/scans.schedule_boundary(now, interval)`.
  - **Celery beat** fires `scans.tick` **every 15 minutes** (`*/15`), so a boundary in any UTC offset (:30, :45) gets a tick on time. Ticks between boundaries find every window already scanned and do nothing. **A new interval applies from the next tick.** Windows still join up: a longer interval waits for its next boundary, and a shorter one starts from `scanned_until`.
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
- **Runtime:** **everything runs in Docker Compose** (db, rabbitmq, redis, api, worker, processor-worker, beat, web), defined in `docker-compose.yml` at the repo root.

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

- Left sidebar: the IDIM logo (with the "I Do It Myself" tagline) and the **notifications bell** at the top, the navigation in the middle, and **only** the day/night toggle at the bottom. The toggle is a switch with a sun icon on its left and a moon icon on its right, and no text.
- **Navigation has at most two levels (owner rule: a maximum, not a requirement).** A top-level section is **either a link itself** (has `path`, no sub-sections, e.g. **Home**) **or** a non-clickable heading over its sub-sections. There is never a third level. The types in `components/layout/nav-config.ts` enforce this (a union of the two shapes). A sub-section can declare an `indicator` component for live status; **Scans shows a spinner while any scan is queued or running** (`ScansActivityIndicator`). Every sub-section also shows **how many items its page lists**, muted and right-aligned (owner, 2026-10-26). Each declares this as a `useCount` hook in `nav-config.ts`.
- Current navigation (in this order): **Home** and **Dashboards** (direct links), then **Automation** › **Scans**, **Labels**, **Filters** and **Processors** (owner's order, 2026-10-26), then **Connections** › **Inboxes** (route kept as `/connections/inbox`, because the Gmail OAuth callback returns there). `/` lands on Home.
- Routes: `/home`, `/dashboards`, `/dashboards/:dashboardId` (a processor's id), `/automation/filters`, `/automation/filters/new` and `/automation/filters/:filterId` (the editor), `/automation/labels`, `/automation/labels/:labelId`, `/automation/processors`, `/automation/processors/:processorId`, `/automation/scans`, `/connections/inbox`.
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
- **DbGate** (database UI, compose profile `development`): `docker compose --profile development up --build`, then http://localhost:3000. It is preconnected to the `db` service (credentials from `.env`) and keeps its settings in `./.data/dbgate`. Plain `docker compose up` leaves it out.
- The Celery **worker** consumes the `scans` queue, **processor-worker** the `processors` queue, and **beat** publishes `scans.tick` and `processors.sweep`. None of them hot-reloads, so run `docker compose restart worker processor-worker beat` after backend changes. Remote control, gossip and mingle are disabled because RabbitMQ 4 rejects the transient queues they need.
- Compose reads `.env` from the repo root.
- **All persistent data is bind-mounted under `./.data/`** (gitignored; owner, 2026-10-26): `postgres`, `rabbitmq`, `redis` and `dbgate`. For a fresh setup, stop the stack and delete `./.data`.
- The older named volumes `idoitmyself_postgres_data`, `idoitmyself_idim_postgres_data` and `idim_idim_postgres_data` came from earlier attempts and are deliberately not used. Do not delete them without asking.
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
- **Colours in the UI:** the colour is picked with `ColorPicker` in the add and edit dialogs. It shows as a `LabelDot` (`features/labels/label-dot.tsx`) beside the label's name everywhere: label rows and page, filter rows and the label picker, email label tags, Home (by label, this month vs last, recent, needs attention) and the label filter. Every API shape that carries a label also carries its `color`. **Label colours are identity dots only, never chart series colours.**
- `GET /api/v1/labels` (each with `email_count` and the `filters` that write it), `GET /api/v1/labels/{id}`, `POST /api/v1/labels` `{display_name, color?}` (201; 409 if the normalised name is taken), `PATCH /api/v1/labels/{id}` `{display_name?, color?}`, `DELETE /api/v1/labels/{id}` (204; **409 while any filter writes it**), `GET /api/v1/labels/{id}/stats?tz`, `GET /api/v1/labels/{id}/emails?page&page_size` (newest first, with the filter that added the label).

### Scanning (Automation › Scans)
- **Tables:**
  - `scans`: inbox, `kind` (`scheduled|adhoc`), status (`queued|running|completed|failed|cancelled`), `window_start`/`window_end` (emails received in `[start, end)`), timestamps, `error`, and counters: `emails_found`, `emails_processed`, `emails_skipped` (already stored), `emails_failed`, `emails_matched`, `labels_applied`, `retries`.
  - `inbox_sync`: one row per inbox, holding `scanned_until`, the end of its last scheduled window. No row means it has never been scanned on schedule.
  - `scan_settings`: the single row holding the scheduled-scan interval (see Scanning above).
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
  - Quota units (Google's quota page, checked 2026-10-26; projects created on or after 1 May 2026): `labels.list` 1, `messages.list` 5, `messages.get` 60 (full; 20 for metadata), `messages.attachments.get` 20.
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

### Processors (Automation › Processors), datasets, dashboards, notifications
- **SDK** (`app/processors/`, exported from `app.processors`; how-to in `.claude/skills/add-processor/SKILL.md`):
  - `records.py`: datasets are `Record` subclasses, e.g. `class Statement(Record, dataset="cards.statements", time="statement_date")`.
    - Each field declares a role: `Dimension`, `Measure`, `Time` or `Text`. `Money` is a Decimal.
    - `kind="snapshot", key=...` means "the latest per key". Every dataset is registered in `DATASETS`; datasets are global and shared between kinds.
  - `kinds.py`: `ProcessorKind` subclasses with a `key` register themselves. `kinds()` imports every package under `app/processors/`.
    - A kind declares `writes`, an optional `config` model, `version` and `dashboard` (a JSON file next to it).
    - It implements `async process(doc, ctx)`.
  - `document.py` (`EmailDocument`: sender/recipients, headers, text and HTML body, lazy `attachments[].read()`, labels, `open_url`, provider extras) and `loader.py` (builds it from the mailbox, with the Redis cache).
  - `context.py`: `write`/`write_all`, `action(…, key, at)`, `secret(name, scope, prompt)` and `pdf_text(doc, attachment)`.
  - `outcomes.py`: `Skip`, `Fail`, `NeedsInput`, `Retry`.
  - `actions.py`: `Notify`.
  - `testing.py`: `make_document`, and `run_kind(kind, doc, pdf_text=…)` for tests with synthetic text.
- **Kinds today:** `cards` (`credit_card_statements`).
  - Writes `cards.statements`: dues, limits, balances, period, fees.
  - Writes `cards.transactions`: date, description, merchant category, kind (purchase, payment, refund, cashback, fee or EMI), direction, amount.
  - Schedules a **due reminder** (Notify) 3 days before the due date, never for past bills.
  - **Parsers:** `cards/parsers/base.StatementParser` is the parent, with shared helpers (`parse_dates` for numeric, `dd/Mon/yyyy`, `18 Oct 26` and `October 12, 2026` dates; `statement(...)`; `transaction(...)` with classification). One child per bank, each written against a real statement:
    - `yes_bank`: phrase-based. The PDF password is the cardholder's DOB as DDMMYYYY.
    - `axis`: tabular rows; columns are told apart by runs of spaces, so it keeps them.
    - `icici`: labels and values sit in separate blocks; amounts are prefixed with "`".
    - `idfc_first`: multi-line transactions. Opening balance, purchases, payments and credit limit are left empty.
    - `au`: three-line transactions (day + description, "Mon yy Dr/Cr" with optional reward points, amount); balances come from the bill summary.
  - **HDFC:** no parser yet (no sample), so its emails are skipped.
  - **Unreadable pages:** `pdf_text` skips a page pypdf can't extract and keeps the rest. Before giving up on a `LimitReachedError`, it trims simple fonts' oversized `/Widths` arrays and retries (pypdf 6.18.1+ rejects more than 256 entries as a DoS guard, GHSA-g9cg-prrw-2r8q; Axis statements carry 257). If nothing extracts, the failure names the page errors instead of calling it a scanned image.
- **Tables** (in `0001`):
  - `processors` (`kind`, `config` JSONB, `status`, `default_key`) and `processor_labels` (n–n; label RESTRICT).
  - `processor_runs`:
    - unique (processor, email);
    - `trigger_label_ids`, `status` (`queued|running|succeeded|skipped|failed|needs_input|cancelled`), `attempts`, `kind_version`, `records_written`;
    - `input_name`, `input_scope` and `input_prompt` for runs waiting on input.
  - `records`:
    - columns: `dataset`, `schema_version`, `processor_id` (SET NULL), `email_id`, `run_id`, `key`, `occurred_at` (the dataset's time field) and `data` (JSONB);
    - indexes: (dataset, occurred_at), (processor_id, email_id), (dataset, key).
  - `input_values`: name and scope, Fernet-encrypted.
  - `actions`: unique (processor, email, key); `type`, `payload`, `run_at`, `status` (`pending|done|failed|cancelled`), `dispatched_at`.
  - `notifications`: unique `action_id` (null for failed-run notices); `read_at`, `telegram_sent_at`, `dismissed_at`.
- **Flow:**
  - **Queuing runs:** `scan_engine._store` inserts labels with `RETURNING`. In the same transaction, `processor_engine.create_runs` queues one run per active processor with any added label (on conflict, nothing). The batch task publishes `processors.run`.
  - **Running:** `run_processor` loads the document (Redis or the mailbox; a Gmail full fetch is 60 units, an attachment 20) and calls `process`. Then, in **one transaction**, it replaces the processor's records for the email and upserts its actions. A delivered action is never redone; a pending one is updated.
  - **Retries:**
    - Transient errors and `Retry` re-publish with back-off, reusing the scan settings. Quota pacing doesn't use an attempt.
    - `processors.run` and `processors.deliver_action` use `acks_late` + `reject_on_worker_lost`.
    - `processors.sweep` (every 5 minutes) re-publishes runs with no progress for `PROCESSOR_STALE_MINUTES`.
  - **Actions:**
    - Actions due now are published right after the run. `processors.actions_tick` (beat, every minute) publishes the rest when due, and re-publishes any dispatched over 10 minutes ago and still pending.
    - `services/actions.deliver` creates the in-app notification (unique per action), then sends to Telegram once (`services/telegram.py`).
    - Telegram 429/5xx are retried. Other errors are noted on the action, and the in-app notification stays.
- **Dataset queries** (`services/datasets.py`):
  - JSON queries are checked against the dataset's fields; nothing from the client reaches SQL as text.
  - `POST /api/v1/datasets/query`: an aggregate (`measure`, `agg` sum|avg|min|max|count|latest, `group_by`, `bucket` day|week|month|year, `filters`, `limit`), scoped by `processor_ids` and `start`/`end`.
  - `POST /api/v1/datasets/rows`: records with their email.
  - `GET /api/v1/datasets`.
  - Snapshot datasets are reduced to the latest record per key before aggregating.
- **Dashboards:**
  - `GET /api/v1/dashboards` and `/{processor_id}`: one per processor whose kind ships a dashboard spec, i.e. the kind's spec over that processor's records. There's no table until the editor (v2).
  - Specs are validated against the datasets (`services/dashboards.check_spec`; tests check every kind's).
  - **Widget types:**
    - `stat`: with "vs previous period";
    - `timeseries`;
    - `composition`: stacked by group; the top five get the categorical `--chart-series-1..5` tokens, the rest fold into "Other";
    - `breakdown`;
    - `table`.
  - Widths: `full`, `half` or `third` of a 6-column grid.
- **Other API:**
  - `GET /api/v1/processors/kinds` (with the datasets each writes)
  - `GET|POST /processors`, `GET|PATCH|DELETE /processors/{id}`: PATCH changes name, description, `label_ids`, `config` and status. DELETE is 409 for defaults, and keeps records.
  - `GET /processors/{id}/runs?status=…`, `POST /processors/{id}/run-existing`, `POST /processors/{id}/rerun?status=failed`
  - `PUT /processors/inputs {name, scope, value}`: re-queues the waiting runs.
  - `GET /api/v1/notifications?page&page_size&unread_only` (with `unread`; dismissed ones are left out), `POST /notifications/{id}/read|unread|dismiss`, `POST /notifications/read-all`. A failed run adds one in `processor_engine._finish`, in the same transaction.
  - Home `attention` includes `inputs_needed`.
- **Frontend:**
  - `features/processors/`: the list; the add/edit dialog (kind and labels multi-select); the detail page (tiles, Dashboard link, run on existing, re-run failed, re-run skipped, a "Needs a look" list with input buttons); and `input-dialog.tsx`, also used on Home.
  - `features/dashboards/`: the list, and the dashboard page with a range select and the widget grid (`widgets.tsx`, `values.ts`).
  - `features/notifications/notifications-bell.tsx`: next to the logo in the sidebar, and on the right of the phone top bar.
    - It shows the unread count and a popover list.
    - Clicking an item opens its email in a new tab and marks it read. Ticking toggles read or unread. × dismisses it. "Mark all read" clears the rest.
    - Updates are optimistic.

### Home, the app-wide landing page (formerly Dashboard)
- Sections, top to bottom:
  1. **Filters**: date range, inbox and labels (kept in the URL).
  2. **Headline tiles**, in this order: **Emails scanned** (opens the emails window), **Active filters** (→ Filters), **Labelled** (→ Labels), **Scans completed** with emails labelled (→ Scans). The header shows "Next scan in X" (`GET /api/v1/scans/schedule`) and a blinking dot when a scan is running. Every section refreshes on its own: every 5 seconds while a scan runs, otherwise every 30 (`useLiveInterval`).
  3. **Needs attention**: inboxes whose last scan failed, problem scans in the last 30 days, inboxes not scanned because no active filter covers their type, active filters that never matched, labels no active filter adds.
  4. **Trends**: emails over time; labelled emails this month vs last, per label.
  5. **Recent activity** (max 5 entries each): latest labelled emails, latest scans.
  6. **Breakdowns**: by label, by filter, top senders, by inbox.
- **Opening an email:** every email list (the Emails window, the label page, Home's recent activity) links each row to the message in its provider's web UI, in a new tab. The backend builds `open_url` with `app.mail.sources.message_url`; for Gmail that's `https://mail.google.com/mail/?authuser=<inbox address>#all/<message id>`, which picks the right signed-in account. On the frontend, `features/emails/email-link.tsx` makes the subject a link stretched over the row; other links in the row sit above it with `relative z-10`.
- **Emails window** (`features/emails/emails-explorer.tsx`): a large dialog over the stored emails. It starts from Home's filters and adds a sender/subject search, labelled / not labelled, and sorting by sent date, sender or subject. It shows stats for every match (emails, labelled, not labelled, senders, inboxes, sent-between) and a paged list with each email's labels and the filter that added them. Backed by `GET /api/v1/emails?start&end&inbox_id&label_id…&labelled&q&sort&page&page_size` (`app/services/emails.py`; the search is a literal ILIKE).
- Endpoints: `GET /api/v1/stats/overview` and `GET /api/v1/home/summary` (scans by **finish time**), and `GET /api/v1/home/attention|status|recent` (`app/services/home.py`). All of it reads stored data only.

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
    app/processors/             # processor SDK (records, document, kinds, context, actions, testing) + kinds (cards/)
    app/services/               # gmail_oauth, inboxes, tags, labels, filters, scans, scan_engine, processors, processor_engine, actions, telegram, notifications, datasets, dashboards, stats, home
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
      features/<feature>/       # home, dashboards, filters, labels, processors, notifications, scans, inboxes, emails, stats
      router.tsx                # routes
docs/filters-revamp-plan.md     # the reviewed plan and owner decisions for the filters revamp
docs/processors-plan.md         # the processors plan and owner decisions (v1, built)
docs/processors-v2-plan.md      # processors v2: SDK, datasets, actions, dashboards (built; derived datasets and the editor later)
.claude/skills/add-processor/   # Claude Code skill: how to add a processor kind or parser
docker-compose.yml              # full dev stack
.env.example                    # env var template — keep in sync when adding config
```

## Working conventions

- Never read, print, or edit `.env` / `.env.back` (real secrets). Use `.env.example` for reference and add any new variables there.
- Keep this file updated when the owner makes a decision that future sessions need to know.
