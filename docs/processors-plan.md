# Processors: plan for review

Status: **superseded by `docs/processors-v2-plan.md` (2026-10-26).** Was implemented 2026-10-26 (credit card statements, with a Yes Bank parser). AGENTS.md › Processors is the current reference. The owner's decisions are in §1 and override anything else in this doc that conflicts with them. The build differs from this draft in these ways:

- **Passwords:** there is no per-processor config or `processor_secrets` table. PDF passwords are saved per **(sender address, label)** in `pdf_passwords`, as entered from the Dashboard warning. Saving one re-runs the waiting emails.
- **Parsers:** a kind picks its child parser by the sender's domain. The user picks the kind, not the bank.
- **No `paused` status.** A wrong or missing password is per sender (`needs_password`), and other failures fail the run.
- **Attachment refs aren't snapshotted.** The run re-fetches the message (Gmail attachment ids can change between fetches) and then downloads the PDF.
- **"Run on existing emails"** covers every labelled email without a result. There's no date range.

## 1. Owner decisions (2026-10-26)

1. The concept is called **Processors**. The chain is **Filter → Label → Processor**.
2. A processor is triggered by **exactly one label**. A label can have many processors.
3. Libraries are added as needed. **LLM calls go through OpenRouter only.**
4. **Processors never send sensitive information to any AI.** AI filter conditions stay as they are: the user opts into them per filter (owner, 2026-10-26). Processors are **deterministic parsers written in code**, one for each document format (e.g. one bank's credit-card statement). No LLM extraction and no OCR.
5. Only the **extracted JSON** is stored. Bodies and attachments (PDFs) are never stored.
6. Processors run on a **new worker service** with its own queue.
7. Deleting a processor **keeps its results**.

## 2. What a processor is, in one paragraph

A **parser** is code: a Python class that reads one kind of document and returns a typed result. A **processor** is a record the user creates. It binds a parser to a trigger label, holds that parser's settings (such as the PDF password) and has a lifecycle (**active / inactive**). When a scan adds the label to an email, every active processor on that label gets a **run**. The processor worker re-reads what the parser needs from the mailbox, parses it, and stores the result as JSON against the email. Results are typed, so analytics can aggregate them later (for example, the total due per card per month).

## 3. Parser catalogue (code)

`app/processors/parsers/`: one module per parser, registered in a catalogue the way `app/filters/fields.py` is. Each parser declares:

| Part | Purpose |
|---|---|
| `key`, `name`, `description` | e.g. `hdfc_cc_statement`, "HDFC credit card statement" |
| `version` | Bumped when the output changes. Every result records it. |
| `Config` (Pydantic) | User settings, e.g. `pdf_password` (secret) and an `attachment_pattern` override. Secret fields are marked as such. |
| `Output` (Pydantic) | The typed result, e.g. `card_last4`, `statement_date`, `due_date`, `total_due`, `minimum_due`, `fees`, `finance_charges`, `currency`. |
| `inputs` | What the parser needs: the body text, and/or attachments matching a pattern (e.g. `*.pdf`). The runner fetches only these. |
| `parse(email, attachments, config) -> Output` | A pure, deterministic function, unit-tested against fixture documents. |

`GET /api/v1/processors/parsers` serves the catalogue: config fields (secret fields flagged) and output fields with their types. The editor and the results table are driven by it.

- **Money** is a string-encoded decimal plus a currency, never a float.
- **Parse outcomes:**
  - `Output`: success.
  - `NotApplicable(reason)`: e.g. no matching attachment, or a promotional email that carries the label. The run is **skipped**, which isn't a failure.
  - `ParseError(reason)`: the document doesn't look like the expected format. The run fails.
- **PDF handling:** text extraction is local. Use `pypdf`, or `pdfplumber` where table layout matters; the choice is made per parser when it's implemented. Decryption uses the password from the config. Image-only PDFs aren't supported (no OCR) and fail with a clear error.

## 4. Data model (into the single `0001` migration)

| Table | Columns (main) | Notes |
|---|---|---|
| `processors` | `id`, `name`, `description?`, `label_id` (FK, RESTRICT), `parser` (catalogue key), `config` (JSONB, secrets excluded), `status` (`active` / `inactive` / `paused`), `paused_reason?`, `status_changed_at`, timestamps | `paused` is set automatically on a fatal error (§6). |
| `processor_secrets` | `processor_id` (PK, CASCADE), `ciphertext` | Secret config fields, **Fernet-encrypted** like `inbox_credentials`. The API is write-only: it reports "set" or "not set" and never returns the value. |
| `processor_runs` | `id`, `processor_id` (SET NULL), `email_id` (CASCADE), `trigger` (`label` / `manual`), `status` (`queued` / `running` / `succeeded` / `skipped` / `failed` / `cancelled`), `attempts`, `error?`, `input_refs` (JSONB: attachment refs snapshotted at scan time), `queued_at`, `started_at`, `finished_at` | Run history, including re-runs. |
| `processor_results` | `id`, `processor_id` (SET NULL), `email_id` (CASCADE), `parser`, `parser_version`, `processor_name` (snapshot), `output` (JSONB), `run_id`, `produced_at`; unique on (`processor_id`, `email_id`) | One current result per processor and email; a re-run overwrites it. `parser` and `processor_name` keep results readable after the processor is deleted (decision 7). |

## 5. Triggering

- **Only a new label triggers a processor.** `process_batch` already inserts `email_labels` with on-conflict-do-nothing. With `RETURNING` it knows which labels are really new. If two filters add the same label, its processors run once.
- **Outbox:** the scan inserts `processor_runs` (`queued`) for every **active** processor on each new label, **in the same transaction** as the labels. It also stores the attachment refs from the `FetchedEmail` it already has. After commit it publishes `processors.run(run_id)`.
  - A beat sweep republishes `queued` runs older than a few minutes.
  - This means a lost message is never lost work. Scans don't have that guarantee today (see Known gaps).
- **Existing emails:** no processor touches past mail on its own, matching "filters apply to new emails only". The user can explicitly ask to **run on emails already labelled**, over a date range, from the processor's page. This creates `manual` runs for emails that don't have a result yet.
- **No chaining:** processors don't add labels.

## 6. Running

- **New compose service `processor-worker`:** a Celery worker on the `processors` queue. Beat gets the sweep task.
- **`MailSource` extension:**
  - `fetch_attachment(message_id, ref) -> bytes`. `Attachment` gains an opaque `ref` and a `size`.
  - Gmail: `messages.attachments.get`, 5 units, reserved through `QuotaBudget` like every other call.
  - Thanks to the snapshotted refs, a PDF parser needs no second `messages.get` (60 units). A parser that needs the body re-fetches the message.
- **Retries:** the same machinery as scans.
  - **Transient** (`TransientError`, `QuotaExhausted`): re-published with a countdown. Quota pacing doesn't use an attempt. After `PROCESSOR_MAX_ATTEMPTS` the run fails.
  - **Fatal for the processor** (wrong PDF password, auth lost): the run fails and the processor is set to **`paused`** with a reason, so it doesn't fail every email. The user fixes the setting and resumes it.
  - **Per email** (`ParseError`): that run fails and the others carry on.
- Bytes live only in worker memory for the duration of the parse.

## 7. Lifecycle

- **New processors** start **active**. Active and inactive are switched like filters. Inactive and paused processors get no new runs; runs already queued still finish.
- **Edits** (name, config, password) apply to runs from then on. The trigger label and the parser are fixed after creation; to change them, create a new processor. That keeps every result tied to one label and one output shape.
- **Re-runs:** "Re-run failed" for a processor, and "Re-run" for one result. Both create `manual` runs.
- **Parser upgrades:** results record `parser_version`, so results from an older version are flagged and can be re-run on request.
- **Deleting a processor:** queued runs are cancelled, and results and runs are kept with `processor_id` set to null (decision 7).
- **Deleting a label:** blocked with 409 while any processor (active, inactive or paused) uses it, like filters (owner, 2026-10-26).

## 8. UI

- **Automation › Processors** (between Labels and Scans): an `ItemList` with a status badge, the trigger label (`LabelDot`), the parser name, and figures for succeeded, failed and last run. The editor is a dialog: a parser picker, a label picker, and config fields generated from the parser's `Config`, with secret fields as password inputs showing "set" or "not set".
- **Test:** pick a recent email with the trigger label, do a dry run and show the output or the error. Nothing is stored.
- **Processor page:**
  - a results table whose columns come from the parser's `Output`, with a link to open each email;
  - CSV export;
  - run history with failures;
  - "Run on existing emails" and "Re-run failed".
- **Elsewhere:**
  - The label page lists its processors.
  - Email rows show their results.
  - Dashboard "Needs attention" adds paused processors and failed runs.
  - The nav gets a spinner while runs are active, like Scans.

## 9. Open questions

None. The first parser is Yes Bank.
