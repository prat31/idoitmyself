# Processors v2: plan for review

Status: **built 2026-10-26**, phases 1–5. AGENTS.md › Processors is the current reference.

**Still to do:** derived datasets (§6), the dashboard editor (v2), and dashboards that mix processors (v3).

**How the build differs from this plan:**
- **No `Needs` declaration:** documents are always built from one full fetch and cached, and attachments are read lazily.
- **No `dashboards` table yet:** a processor's dashboard is its kind's spec, read from code. The table arrives with the editor.
- **Only the `Notify` action** is built (in-app, plus Telegram when configured); `Webhook` comes later.
- **Owner's answers to §12:**
  1. In-app notifications plus Telegram (bot token and chat id from env, skipped silently if unset).
  2. The old Dashboard is renamed Home, and Dashboards is a new top-level section.
  3. The order of work is as proposed.

## 1. Owner decisions (2026-10-26)

1. **Processors ↔ labels is n–n.**
   - An email runs through a processor when it newly gets **any** of the processor's labels.
   - A label can trigger many processors.
2. **There's one standard input object per email** (`EmailDocument`).
   - Every processor receives it.
   - Its built form may be **cached in Redis**, encrypted and short-lived, so several processors share one fetch.
3. **Processors run as Celery tasks** that are retryable, idempotent and durable. They write **outputs** that dashboards are built from.
4. **Dashboards:**
   - Every processor gets one.
   - **Dashboards that combine several processors' data** must be possible eventually.
   - How much can be built in the UI grows over time.
5. **Processors may have side effects** (alerts, notifications, webhooks), not just data.
6. **Processors are code only**, but writing one must be intuitive, generic and easy. A **Claude Code skill** guides adding one.
7. **No restrictions on instances:** a kind can have any number of processors, each with its own labels.
8. **State across emails:** the agent's recommendation, in §6, which is derived datasets.

## 2. Concepts

| Concept | What it is | Where it lives |
|---|---|---|
| **Processor kind** | A Python class: what it reads, what it writes, how. E.g. credit card statements. | Code (`app/processors/<kind>/`) |
| **Processor** | An instance of a kind: name, labels (n–n), config, status. | DB, created in the UI or as a default |
| **Run** | One processor on one email. Unique per (processor, email). | DB (`processor_runs`) |
| **EmailDocument** | The standard, versioned input object for one email. | Built in the worker; cached in Redis |
| **Dataset** | A named, typed table of records, e.g. `cards.statements`. Shared: several kinds may write the same dataset. | Schema in code |
| **Record** | One row of a dataset, linked to its email, run and processor. | DB (`records`) |
| **Derived dataset** | Records computed from other datasets, e.g. portfolio holdings from trades. | Function in code; rows in `records` |
| **Action** | A side effect a processor asks for, e.g. "notify: bill due in 3 days". Delivered at most once. | DB (`actions`) and the actions task |
| **Input request** | Something a run needs from the user, e.g. a PDF password. Generalises today's PDF-password flow. | DB; shown on the Dashboard |
| **Dashboard** | A JSON spec: a grid of widgets, each a query over one dataset. | DB (`dashboards`); defaults ship with kinds |

## 3. Triggering and runs

- **Labels:** `processor_labels (processor_id, label_id)` replaces `processors.label_id`. A label can't be deleted while a processor uses it, as today.
- **Queuing runs:** when a scan adds labels to an email (the same transaction, the outbox as today), it queues a run for every active processor that has **any** of those labels.
  - `processor_runs` is unique on (processor_id, email_id), so a second matching label (now or in a later scan) adds no run.
  - The run records **which labels triggered it**.
- **Durability:**
  - The broker carries only `run_id`.
  - The processor queue switches to `acks_late` + `reject_on_worker_lost`, which gives at-least-once delivery. That's safe because runs are idempotent (§5).
  - The existing sweep republishes runs that lost their message.
- **Retries:** transient errors (provider, network, quota) re-publish with back-off and never sleep, as today. A kind can raise `Retry(after=…)` itself too.
- **Kinds of trigger:** label (automatic), "run on existing emails" and "re-run" (manual), and **kind upgrade**. When a kind's `version` changes, its results can be re-run.

## 4. The standard input: `EmailDocument`

One provider-agnostic object, versioned with `schema_version`:

| Section | Contents |
|---|---|
| `id`, `inbox` | IDIM email id; inbox id, name, address and mailbox type; provider message and thread ids; Message-ID |
| `sender`, `recipients` | from (name, address, domain); to, cc, bcc-if-known and reply-to as parsed address lists |
| `subject`, `sent_at`, `received_at`, `headers` | every header, lowercased; plus `list_id`, `is_reply`, `in_reply_to` |
| `body` | `text` (plain), `html`, `size` |
| `attachments` | name, mime type, size, and `await read()` (lazy, cached) |
| `labels` | every IDIM label on the email, with the filter and scan that added it; `trigger_labels` for this run |
| `provider` | the mailbox type's own extras (e.g. Gmail category or labels). Kept separate so kinds stay generic. |

- **Needs:** a kind declares what it uses, e.g. `needs = Needs(body=True, attachments=["application/pdf"])`. The builder fetches only that, which saves quota.
- **Cache (decision 2):**
  - **The document:** Fernet-encrypted in Redis under `emaildoc:{email_id}`, with a 1-hour TTL. The first run that needs it builds it, and others reuse it. On a cache miss it's rebuilt from the provider, so the cache is only an optimisation.
  - **Attachment bytes:** cached the same way under `emaildoc:{email_id}:att:{n}`, with a size cap (e.g. 10 MB). Anything bigger is read straight from the provider.
  - **Permanent storage:** none, so bodies and attachments are still never stored for good.

## 5. Writing a processor (the developer API)

Everything a kind needs is in one folder, and the engine does the plumbing: building the document, transactions, idempotency, retries, input requests and actions. The goal is a typical kind of around 50–100 lines of real logic.

```python
# app/processors/cards/datasets.py — shared datasets (any kind may write them)
class Statement(Record, dataset="cards.statements", kind="event"):
    card: str = Dimension(title="Card")
    bank: str = Dimension(title="Bank")
    statement_date: date = Time(title="Statement date")
    due_date: date = Time(title="Due date")
    total_due: Money = Measure(title="Total due")
    minimum_due: Money | None = Measure(title="Minimum due")
    fees: Money = Measure(title="Fees & charges")

class CardTransaction(Record, dataset="cards.transactions", kind="event"):
    card: str = Dimension(title="Card")
    date: date = Time(title="Date")
    description: str = Text(title="Description")
    category: str | None = Dimension(title="Category")
    amount: Money = Measure(title="Amount")
    direction: Literal["debit", "credit"] = Dimension(title="Debit / credit")
```

```python
# app/processors/cards/statements.py — the kind
class CreditCardStatements(ProcessorKind):
    key = "credit_card_statements"
    name = "Credit card statements"
    description = "Reads statement PDFs: dues, fees and transactions."
    version = 1
    needs = Needs(attachments=["application/pdf"])
    writes = [Statement, CardTransaction]
    dashboard = "cards/dashboard.json"  # its default dashboard
    parsers = [YesBankStatement(), IdfcFirstStatement()]  # children, picked by sender

    async def process(self, doc: EmailDocument, ctx: Context) -> None:
        parser = pick_by_sender(self.parsers, doc.sender)  # raises Skip("No parser for …")
        pdf = doc.attachments.first("application/pdf")     # raises Skip("No PDF")
        text = await ctx.pdf_text(pdf)                     # asks the user for the password if needed
        statement, transactions = parser.parse(text)
        ctx.write(statement)
        ctx.write_all(transactions)
        ctx.action(Notify(f"{statement.bank} bill due", due=statement.due_date),
                   at=statement.due_date - timedelta(days=3), key="due-reminder")
```

**What the engine guarantees:**
- **Idempotent writes:** `ctx.write` only buffers. When `process` returns, the engine **replaces** that processor's records for that email in one transaction. Re-runs and duplicate deliveries therefore never double-count.
- **Outcomes by exception:**
  - `Skip(reason)`: nothing to do.
  - `Fail(reason)`: this run fails.
  - `NeedsInput(...)`: wait for the user (§9).
  - `Retry(after)`: transient.
  - Anything else counts as a failure.
- **Ready-made helpers:** `ctx.pdf_text`, `ctx.secret(name, scope)`, `ctx.config` (the processor's validated config, a Pydantic model the kind may declare), `ctx.log`.
- **Nothing to register by hand:** kinds and datasets are discovered from `app/processors/*/`.
- **Testing:** every kind gets a fixture-based test harness, `run_kind(KindClass, fake_document)`, which returns what it wrote and asked for. It needs no DB, broker or provider.

## 6. State across emails: derived datasets (recommendation for decision 8)

Processors stay **stateless per email**: one email in, records out. Running state is computed separately.

- **How:** a **derived dataset** is a pure function from source datasets to rows, e.g. `cards.monthly` from `cards.statements`, `invest.holdings` from `invest.trades`, or goal progress from any measure.
- **When:** recomputed by a debounced Celery task after its sources change, at most once a minute per dataset. Each recompute fully replaces the dataset.
- **Why:**
  - Results don't depend on the order emails arrive in.
  - Re-processing an old email fixes the state automatically.
  - No processor ever holds state that can drift.
- **Milestones and goals** (later) are just derived datasets plus a widget.

## 7. Storage

```
records(
  id, dataset, schema_version,
  processor_id  -> processors  ON DELETE SET NULL,   -- results outlive the processor
  email_id      -> emails      ON DELETE CASCADE,    -- null for derived rows
  run_id, key,                                        -- key: snapshot identity (e.g. holding symbol)
  occurred_at,                                        -- the dataset's main time column, promoted
  data JSONB,                                         -- the record, validated against its schema
  created_at)
index (dataset, occurred_at), (processor_id, email_id), (dataset, key)
```

- **Two dataset kinds:**
  - **`event`:** rows only add up, e.g. bills and transactions.
  - **`snapshot`:** "latest per key as of a date", e.g. card limits and holdings.
- **Why one JSONB table is enough:** a personal mailbox produces thousands of rows, not millions. If one dataset ever needs speed, it gets expression indexes without changing the model.
- **Migrating today's results:** `processor_results` becomes `records`. There's no data to keep, since the stack was just reset.

## 8. Actions (side effects)

- **Requesting one:** `ctx.action(...)` is buffered like writes and saved in the same transaction, in `actions` (processor, email, `key`, type, payload, `run_at`, status). It's unique on (processor, email, key), so a re-run **never sends twice**.
- **Delivering:** an `actions` Celery task delivers each action when due. A beat tick picks up scheduled ones, e.g. "3 days before the due date". Retries and back-off work as everywhere else.
- **Action types** are code, like widgets:
  - `Notify`: an in-app notification feed first; channels later (§12).
  - `Webhook`: an HTTP POST.

## 9. Input requests (generalising PDF passwords)

- **How a kind asks:** it calls `ctx.secret("pdf_password", scope=(sender, label))` or `ctx.pdf_text(...)`. If the value is missing or wrong, the engine raises `NeedsInput`, and the run waits as `needs_input`.
- **Where the user answers:** the Dashboard's Needs attention panel asks for it, with a link to the email. That's today's flow, made generic.
- **After answering:** values are stored Fernet-encrypted, per (name, scope). Saving one queues every run waiting on it.

## 10. Dashboards

- **Spec:** `dashboards(id, name, processor_id nullable, default_key, spec JSONB)`. A spec is a grid of widgets, and every widget is `{type, title, query, options}`.
- **Widget types** (code; the chart components we already have):
  - stat tile (with change vs. the previous period);
  - time series (columns);
  - breakdown (bar list);
  - composition (stacked or 100% bars);
  - table, with drill-down to emails;
  - later, goal/milestone.
- **Query** (a JSON shape, validated against the dataset schemas):
  - `dataset`
  - `measure` + `agg` (sum, avg, count, min, max, latest)
  - `group_by` (a dimension)
  - `bucket` (day, week, month, year)
  - `filters` (dimension values, date range, processor)
  - `compare` (the previous period)
- **Endpoint:** `POST /api/v1/datasets/query`. It builds SQL from whitelisted columns only, never raw SQL from the client.
- **Across processors (decision 4):** datasets are global and shared, and every widget names its own dataset. One dashboard can therefore mix them, e.g. card spend next to investments. A dataset several kinds write gives a combined view automatically.
- **What the UI can build, in stages:**
  1. **v1:** every kind ships a default dashboard (seeded like the other defaults), read-only in the UI.
  2. **v2:** an editor to add, edit and remove widgets by picking dataset → measure → group by → chart.
  3. **v3:** user-made dashboards in their own nav section, mixing datasets.

## 11. The Claude Code skill: `add-processor`

`.claude/skills/add-processor/SKILL.md`. It's written once the SDK in §5 exists, so it describes real code. It walks through:
1. Choosing or creating datasets: reuse shared ones before adding new ones.
2. Scaffolding `app/processors/<kind>/` (kind, parsers, datasets, `dashboard.json`).
3. Implementing `process` with the helpers in §5.
4. Writing tests with synthetic fixtures. **Never commit real statements or personal data.**
5. Optionally adding a built-in default processor in `app/defaults.py`.
6. Running the checks, and updating AGENTS.md.

## 12. Open questions

1. **Notification channels:** is an in-app notification feed enough at first? If not, which channel comes first (email, Telegram, push)?
2. **Dashboards in the nav:** under each processor's page, or a new top-level **Dashboards** section (needed for v3 anyway)?
3. **Order of work:** the proposal is
   1. SDK and engine (n–n triggers, EmailDocument and cache, records, input requests);
   2. port credit cards (Yes Bank, then IDFC FIRST);
   3. query endpoint and dashboard v1;
   4. the skill;
   5. actions;
   6. derived datasets;
   7. dashboard editor (v2), then cross-processor dashboards (v3).
