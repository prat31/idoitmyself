from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.retry import TransientError


@dataclass(frozen=True)
class Attachment:
    """A file attached to an email (name and type only; content is never downloaded)."""

    filename: str
    mime_type: str


@dataclass(frozen=True)
class FetchedEmail:
    """A provider-agnostic email as read from a mailbox. `body_text` is used for classification only
    and is never stored."""

    provider_message_id: str
    provider_thread_id: str | None
    internet_message_id: str | None
    sent_at: datetime
    from_address: str | None
    to_addresses: str | None
    cc_addresses: str | None
    subject: str | None
    snippet: str | None
    body_text: str
    attachments: tuple[Attachment, ...] = ()


class MailSourceError(Exception):
    """A failure reading from a mailbox that retrying won't fix (auth, not found). Safe to show."""


class TransientMailSourceError(MailSourceError, TransientError):
    """A mailbox failure worth retrying later (rate limit, 5xx, network)."""


class MailSource(Protocol):
    """Read access to one inbox. Each provider implements this; run logic only depends on it."""

    async def list_message_ids(self, start: datetime, end: datetime) -> list[str]:
        """Ids of messages whose sent/received time is in [start, end)."""
        ...

    async def fetch(self, message_id: str) -> FetchedEmail: ...
