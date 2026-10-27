"""EmailDocument: the one standard, provider-agnostic object every processor receives for an email.

Built once per email from the mailbox (bodies and attachments are never stored), then kept in Redis,
Fernet-encrypted, for DOCUMENT_TTL so every processor on the email shares one fetch. Attachments are
read lazily (`await attachment.read()`) and cached the same way up to ATTACHMENT_CACHE_MAX_BYTES."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from email.utils import getaddresses
from typing import Any, ClassVar

from pydantic import BaseModel, PrivateAttr

from app.processors.pdf import is_pdf

AttachmentReader = Callable[["Attachment"], Awaitable[bytes]]


class Address(BaseModel):
    name: str | None
    address: str  # lowercase
    domain: str

    @classmethod
    def parse_all(cls, header: str | None) -> list["Address"]:
        found: list[Address] = []
        for name, address in getaddresses([header or ""]):
            address = address.strip().lower()
            if "@" in address:
                found.append(
                    cls(name=name.strip() or None, address=address, domain=address.rpartition("@")[2])
                )
        return found


class Attachment(BaseModel):
    filename: str
    mime_type: str
    size: int | None  # bytes, if the provider says
    ref: str | None  # the provider's id for it

    _reader: AttachmentReader | None = PrivateAttr(default=None)

    @property
    def is_pdf(self) -> bool:
        return is_pdf(self.filename, self.mime_type)

    async def read(self) -> bytes:
        """The attachment's content, from the cache or the mailbox."""
        if self._reader is None or self.ref is None:
            raise RuntimeError(f"{self.filename} can't be read")
        return await self._reader(self)


class Inbox(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    mailbox_type: str


class EmailLabel(BaseModel):
    id: uuid.UUID
    name: str  # normalised
    display_name: str
    filter_id: uuid.UUID | None  # the filter that added it


class EmailDocument(BaseModel):
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_version: int = SCHEMA_VERSION
    id: uuid.UUID  # IDIM's email id
    inbox: Inbox
    provider_message_id: str
    provider_thread_id: str | None
    message_id: str | None  # RFC 5322 Message-ID
    # Opens the message in the provider's web UI, if it has one.
    open_url: str | None

    sender: Address | None
    to: list[Address]
    cc: list[Address]
    reply_to: list[Address]
    subject: str | None
    sent_at: datetime
    headers: dict[str, str]  # every header, by lowercase name
    list_id: str | None
    is_reply: bool

    body_text: str
    body_html: str | None
    size: int | None

    attachments: list[Attachment]
    labels: list[EmailLabel]  # every IDIM label on the email
    # The mailbox type's own extras (e.g. Gmail's category and labels): kinds stay generic without them.
    provider: dict[str, Any]

    def bind(self, reader: AttachmentReader) -> "EmailDocument":
        for attachment in self.attachments:
            attachment._reader = reader
        return self

    def pdfs(self) -> list[Attachment]:
        return [a for a in self.attachments if a.is_pdf]
