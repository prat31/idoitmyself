from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.core.retry import TransientError


@dataclass(frozen=True)
class Attachment:
    """A file attached to an email: name and type. Scans never download its content; processors do,
    with `ref` (the provider's opaque id for it, if it has one)."""

    filename: str
    mime_type: str
    ref: str | None = field(default=None, compare=False)
    size: int | None = field(default=None, compare=False)  # bytes, if the provider says


@dataclass(frozen=True)
class FetchedEmail:
    """A provider-agnostic email as read from a mailbox. Bodies are used for filtering and processors,
    and never stored."""

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
    # Every header, keyed by lowercase name (repeated headers joined with ", ").
    headers: dict[str, str] = field(default_factory=dict)
    size_bytes: int | None = None
    # Values for the provider's own filter fields (see app.filters.fields), e.g. Gmail's category.
    provider_fields: dict[str, Any] = field(default_factory=dict)
    body_html: str | None = None


class MailSourceError(Exception):
    """A failure reading from a mailbox that retrying won't fix (auth, not found). Safe to show."""


class TransientMailSourceError(MailSourceError, TransientError):
    """A mailbox failure worth retrying later (rate limit, 5xx, network)."""


class MailSource(Protocol):
    """Read access to one inbox. Each provider implements this; scan logic only depends on it."""

    async def list_message_ids(self, start: datetime, end: datetime) -> list[str]:
        """Ids of messages received in [start, end)."""
        ...

    async def fetch(self, message_id: str) -> FetchedEmail: ...

    async def fetch_attachment(self, message_id: str, ref: str) -> bytes:
        """The content of an attachment, by the `ref` that fetch() gave it."""
        ...
