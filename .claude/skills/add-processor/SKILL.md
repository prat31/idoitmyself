---
name: add-processor
description: Add a new IDIM processor kind (code that reads emails with certain labels and writes records into datasets, asks for side effects like notifications, or asks the user for input), or a new parser for an existing kind (e.g. another bank's credit card statement). Use when asked to "add a processor", "parse X emails", "extract data from Y statements", or "support bank Z".
---

# Adding a processor to IDIM

A **processor kind** is Python code in `src/backend/app/processors/<package>/`. Users create
**processors** (instances of a kind) in the UI and attach labels. Whenever an email newly gets one
of those labels, the engine runs the kind's `process(doc, ctx)` on it, once per processor and email.
The engine handles fetching, caching, retries, idempotent writes and actions.
Read `docs/processors-v2-plan.md` for the model, and AGENTS.md › Processors for what's built.

Ground rules (from AGENTS.md):
- **Deterministic code only.** Never send email content to any AI.
- Ask the owner before adding a backend dependency.
- **Never commit real emails, statements or personal data.** Test with synthetic text that has the
  same layout. If the owner gives a sample file, read it only to learn the layout; it must stay out of git.
- Don't commit or push.

## 0. Decide: new kind, or new parser for an existing kind?

- **Another bank's credit card statement:** add a parser to `app/processors/cards/parsers/`.
  - Subclass `StatementParser` and set `key`, `bank` and `sender_domains`.
  - Read its layout one of two ways:
    - **Labels next to values:** set `phrases` and `transaction_line` and use the default `parse` (like `yes_bank.py`).
    - **Scattered values or tables:** override `parse` and build the result with the base's `statement(...)`, `transaction(...)`, `money` and `parse_dates` (like `axis.py`, `icici.py`, `idfc_first.py`).
  - Register it in `PARSERS` in `cards/statements.py`.
  - Add a synthetic test in the bank's layout to `tests/test_processor_cards.py`.
  - In the app, use **Re-run skipped** on the processor's page to process that bank's bills skipped so far.
  - Then go to step 6.
- **A new kind of document or data:** continue below.

## 1. Datasets: reuse first

List them with `GET /api/v1/datasets`, or read the `Record` subclasses under `app/processors/*/datasets.py`.
**Reuse an existing dataset when the meaning matches** (e.g. card spend from alert emails →
`cards.transactions`). Shared datasets are what make cross-processor dashboards work.

A new dataset is a `Record` subclass in `<package>/datasets.py`:

```python
import datetime as dt  # a field named `date` would clash with the type
from app.processors import Dimension, Measure, Money, Record, Text, Time

class Trade(Record, dataset="invest.trades", label="Trades", time="traded_on"):
    symbol: str = Dimension(title="Symbol")           # group/filter by it
    side: Literal["buy", "sell"] = Dimension(title="Side")
    traded_on: dt.date = Time(title="Trade date")     # `time=` picks the main Time field
    quantity: float = Measure(title="Quantity")       # aggregate it
    amount: Money = Measure(title="Amount")           # Money = Decimal, JSON as a string
    note: str | None = Text(None, title="Note")       # shown in tables only
```

- **Name:** `<domain>.<plural>`, lowercase.
- **Snapshots:** "the latest state per thing" (e.g. holdings) use `kind="snapshot", key="symbol"`.
- **Schema changes:** bump `version=` when you change a dataset's fields.

## 2. The kind

`<package>/<kind>.py`. Export it from `<package>/__init__.py`; importing the package registers it.

```python
from app.processors import Context, EmailDocument, Fail, Notify, ProcessorKind, Skip

class ContractNotes(ProcessorKind):
    key = "contract_notes"            # stable: stored on processors
    name = "Contract notes"
    description = "Reads broker contract notes: every trade."
    version = 1                       # bump when what it writes changes
    writes = (Trade,)                 # writing anything else fails the run
    dashboard = "dashboard.json"      # optional default dashboard, next to this file

    async def process(self, doc: EmailDocument, ctx: Context) -> None:
        pdfs = doc.pdfs()
        if not pdfs:
            raise Skip("No PDF attached")             # nothing to do; not a failure
        text = await ctx.pdf_text(doc, pdfs[0])       # asks the user for the PDF password if needed
        trades = parse(text)                          # raise Fail("…") if it isn't what you expect
        ctx.write_all(trades)
        ctx.action(Notify(title=f"{len(trades)} trades booked"), key="booked")
```

What `doc` (EmailDocument) offers:
- `sender` (`.address`, `.domain`, `.name`), `to`, `cc`, `subject`, `sent_at` and `headers`;
- `body_text`, `body_html`;
- `attachments` (`await a.read()`) and `pdfs()`;
- `labels` (IDIM labels), `open_url`, and `provider` (mailbox-specific extras: avoid relying on them).

What `ctx` offers:
- `write`, `write_all`: buffered. On success they **replace** this processor's records for the email
  in one transaction, so re-runs never double-count.
- `action(Notify(...), key=..., at=datetime)`: delivered once (in-app, plus Telegram if configured).
  The same `key` on a re-run updates a pending action and never repeats a delivered one. Don't
  schedule reminders for the past.
- `secret(name, scope, prompt)`: a value the user types once per scope. The run waits as
  `needs_input`, and the Home page asks for it.
- `pdf_text(doc, attachment)`: the PDF's text, handling the password via `secret`.
- `config`: the processor's settings, if the kind declares a `config` Pydantic model.

End a run other than by returning with these, from `app.processors`:
- `Skip(reason)`: nothing to do;
- `Fail(reason)`: the email can't be processed;
- `NeedsInput(...)`: the run waits for the user;
- `Retry(message, after=seconds)`: try again later.

## 3. Default dashboard (optional, recommended)

`<package>/dashboard.json`:

```json
{ "default_range": "12m", "widgets": [
  { "id": "spend", "type": "stat", "title": "Spend", "width": "third",
    "query": { "dataset": "cards.transactions", "measure": "amount", "agg": "sum",
               "filters": [{ "field": "kind", "values": ["purchase"] }] } },
  { "id": "by-month", "type": "composition", "title": "By month", "width": "full",
    "query": { "dataset": "cards.statements", "measure": "total_due", "bucket": "month", "group_by": "card" } }
]}
```

**Widget types:**
- `stat`: one value, with the change from the previous period;
- `timeseries`: needs `bucket`;
- `composition`: needs `bucket` and `group_by`; stacked, top five plus "Other";
- `breakdown`: needs `group_by`; takes an optional `limit`;
- `table`: `columns` names the fields to show.

**Query fields:**
- `measure` must be a Measure field;
- `group_by` and filters take Dimension or Text fields;
- `agg` is one of `sum|avg|min|max|count|latest`;
- `bucket` is one of `day|week|month|year`;
- `width` is one of `full|half|third`.

A test checks every kind's dashboard against its datasets.

## 4. Tests (synthetic only)

`src/backend/tests/test_processor_<package>.py`, using the harness. No database, broker or mailbox:

```python
from app.processors import kinds
from app.processors.testing import make_document, run_kind

async def test_reads_a_contract_note():
    doc = make_document(sender="notes@broker.example", attachments=[("note.pdf", "application/pdf")],
                        labels=["contract_note"])
    ctx = await run_kind(kinds()["contract_notes"], doc, pdf_text=SYNTHETIC_TEXT)
    assert ctx.records == [...]
    assert ctx.actions[0].key == "booked"
```

Cover:
- the happy path;
- every `Skip` and `Fail`;
- edge cases of the layout: amounts with Indian grouping (`1,00,000.00`), Cr/Dr, missing optional fields;
- that actions aren't scheduled in the past.

## 5. Optionally ship it as a built-in default

To have every install start with it, add a `DefaultProcessor` (and any `DefaultLabel` or
`DefaultFilter` it needs) in `src/backend/app/defaults.py`. It's seeded once on startup, can't be
deleted, and `tests/test_defaults.py` validates it.

## 6. Check and document

```bash
cd src/backend && uv run ruff check . && uv run ruff format --check app tests && uv run pytest
```

Then:
- Run `docker compose restart processor-worker api`; neither hot-reloads processor code reliably.
- Update AGENTS.md › Processors (kinds and datasets list).
- In the UI, create a processor of the new kind on its labels, then use **Run on existing emails** on
  its page. **Only do this when the owner asks:** it reads their real mailbox.
