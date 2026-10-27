"""What a processor's `process` gets besides the email: where to write, how to ask for things."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.processors.actions import ActionType
from app.processors.document import Attachment, EmailDocument, EmailLabel
from app.processors.outcomes import NeedsInput
from app.processors.pdf import PdfPasswordRequired, pdf_text
from app.processors.records import Record

# (name, scope) -> the value the user saved, or None
SecretLookup = Callable[[str, str], Awaitable[str | None]]

PDF_PASSWORD = "pdf_password"
# Inputs typed hidden when asked for (passwords and the like).
SECRET_INPUTS = frozenset({PDF_PASSWORD})


@dataclass(frozen=True)
class PlannedAction:
    key: str
    action: ActionType
    at: datetime | None  # None: now


@dataclass
class Context:
    processor_id: uuid.UUID | None
    processor_name: str
    config: BaseModel | None
    # The processor's labels on the email that triggered this run.
    trigger_labels: list[EmailLabel]
    secrets: SecretLookup
    allowed: tuple[type[Record], ...]  # the kind's `writes`
    records: list[Record] = field(default_factory=list)
    actions: list[PlannedAction] = field(default_factory=list)

    def write(self, record: Record) -> None:
        """Buffer a record. When `process` returns, the processor's records for this email are replaced
        by everything written, in one transaction (so re-runs never double-count)."""
        if not isinstance(record, self.allowed):
            raise TypeError(f"{type(record).__name__} isn't in the kind's `writes`")
        self.records.append(record)

    def write_all(self, records: list[Record]) -> None:
        for record in records:
            self.write(record)

    def action(self, action: ActionType, *, key: str, at: datetime | None = None) -> None:
        """Ask for a side effect, delivered once when due (`at`, or now). `key` names it within this
        email: a re-run with the same key updates a pending one and never repeats a delivered one."""
        self.actions.append(PlannedAction(key, action, at))

    async def secret(self, name: str, scope: str, prompt: str) -> str:
        """A value the user gives once per name and scope (e.g. a password for one sender). Without one
        the run waits, and the Home page asks the user with `prompt`."""
        value = await self.secrets(name, scope)
        if value is None:
            raise NeedsInput(name, scope, prompt)
        return value

    async def pdf_text(self, doc: EmailDocument, attachment: Attachment, *, scope: str | None = None) -> str:
        """The PDF's text. A protected one needs the password saved for its sender and the triggering
        label (or `scope`); the user is asked for it when there's none or it's wrong."""
        data = await attachment.read()
        try:
            return pdf_text(data, None)
        except PdfPasswordRequired:
            pass
        sender = doc.sender.address if doc.sender else "unknown sender"
        label = self.trigger_labels[0] if self.trigger_labels else None
        scope = scope or f"{sender}|{label.name if label else '*'}"
        prompt = f"PDF password for {sender}" + (f" ({label.display_name})" if label else "")
        password = await self.secret(PDF_PASSWORD, scope, prompt)
        try:
            return pdf_text(data, password)
        except PdfPasswordRequired:
            raise NeedsInput(PDF_PASSWORD, scope, prompt, wrong=True) from None

    def summary(self) -> dict[str, Any]:
        return {"records": len(self.records), "actions": len(self.actions)}
