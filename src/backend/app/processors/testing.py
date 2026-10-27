"""Running a kind in tests, with no database, broker or mailbox:

    ctx = await run_kind(MyKind(), make_document(subject="..."), pdf_text="...statement text...")
    assert ctx.records == [...]

`pdf_text` stands in for the PDF's text (so tests use synthetic text, never real documents)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.processors.context import Context
from app.processors.document import Address, Attachment, EmailDocument, EmailLabel
from app.processors.kinds import ProcessorKind


def make_document(
    *,
    sender: str = "Sender <sender@example.com>",
    subject: str = "Subject",
    body_text: str = "",
    attachments: list[tuple[str, str]] = (),  # type: ignore[assignment]
    labels: list[str] = (),  # type: ignore[assignment]
    **overrides: Any,
) -> EmailDocument:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "inbox": {"id": uuid.uuid4(), "name": "Inbox", "address": "me@example.com", "mailbox_type": "gmail"},
        "provider_message_id": "m1",
        "provider_thread_id": "t1",
        "message_id": "<m1@example.com>",
        "open_url": None,
        "sender": next(iter(Address.parse_all(sender)), None),
        "to": Address.parse_all("Me <me@example.com>"),
        "cc": [],
        "reply_to": [],
        "subject": subject,
        "sent_at": datetime(2026, 10, 21, tzinfo=UTC),
        "headers": {},
        "list_id": None,
        "is_reply": False,
        "body_text": body_text,
        "body_html": None,
        "size": None,
        "attachments": [
            Attachment(filename=name, mime_type=mime, size=None, ref=f"a{i}")
            for i, (name, mime) in enumerate(attachments)
        ],
        "labels": [
            EmailLabel(
                id=uuid.uuid4(), name=name, display_name=name.replace("_", " ").capitalize(), filter_id=None
            )
            for name in labels
        ],
        "provider": {},
    }
    return EmailDocument(**(values | overrides))


class _TestContext(Context):
    fake_pdf_text: str | None = None

    async def pdf_text(self, doc: EmailDocument, attachment: Attachment, *, scope: str | None = None) -> str:
        if self.fake_pdf_text is None:
            return await super().pdf_text(doc, attachment, scope=scope)
        return self.fake_pdf_text


async def run_kind(
    kind: ProcessorKind,
    doc: EmailDocument,
    *,
    pdf_text: str | None = None,
    secrets: dict[tuple[str, str], str] | None = None,
    config: dict[str, Any] | None = None,
) -> Context:
    """Run `kind.process` and return the context: what it wrote (`records`) and asked for (`actions`).
    Outcomes (Skip, Fail, NeedsInput, Retry) propagate. Every label on the document counts as a trigger."""
    saved = secrets or {}

    async def lookup(name: str, scope: str) -> str | None:
        return saved.get((name, scope))

    ctx = _TestContext(
        processor_id=None,
        processor_name="Test",
        config=kind.config.model_validate(config or {}) if kind.config else None,
        trigger_labels=list(doc.labels),
        secrets=lookup,
        allowed=kind.writes,
    )
    ctx.fake_pdf_text = pdf_text
    await kind.process(doc, ctx)
    return ctx
