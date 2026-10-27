"""Builds an email's EmailDocument (from the mailbox) and caches it, and its attachments, in Redis."""

import hashlib
import logging
import uuid
from collections.abc import Callable

from cryptography.fernet import InvalidToken
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, decrypt_bytes, encrypt, encrypt_bytes
from app.mail.sources import message_url
from app.mail.types import FetchedEmail, MailSource
from app.models.email import Email
from app.models.email import EmailLabel as EmailLabelRow
from app.models.inbox import Inbox
from app.models.label import Label
from app.processors.document import Address, Attachment, EmailDocument, EmailLabel

logger = logging.getLogger(__name__)

DOCUMENT_TTL = 3600  # seconds
ATTACHMENT_CACHE_MAX_BYTES = 10 * 1024 * 1024


def _key(email_id: uuid.UUID) -> str:
    return f"emaildoc:{email_id}"


def build_document(
    email: Email, inbox: Inbox, fetched: FetchedEmail, labels: list[EmailLabel]
) -> EmailDocument:
    headers = fetched.headers
    return EmailDocument(
        id=email.id,
        inbox={
            "id": inbox.id,
            "name": inbox.name,
            "address": inbox.email_address,
            "mailbox_type": inbox.provider,
        },
        provider_message_id=fetched.provider_message_id,
        provider_thread_id=fetched.provider_thread_id,
        message_id=fetched.internet_message_id,
        open_url=message_url(inbox.provider, inbox.email_address, fetched.provider_message_id),
        sender=next(iter(Address.parse_all(fetched.from_address)), None),
        to=Address.parse_all(fetched.to_addresses),
        cc=Address.parse_all(fetched.cc_addresses),
        reply_to=Address.parse_all(headers.get("reply-to")),
        subject=fetched.subject,
        sent_at=fetched.sent_at,
        headers=headers,
        list_id=headers.get("list-id"),
        is_reply="in-reply-to" in headers or "references" in headers,
        body_text=fetched.body_text,
        body_html=fetched.body_html,
        size=fetched.size_bytes,
        attachments=[
            Attachment(filename=a.filename, mime_type=a.mime_type, size=a.size, ref=a.ref)
            for a in fetched.attachments
        ],
        labels=labels,
        provider=fetched.provider_fields,
    )


async def email_labels(session: AsyncSession, email_id: uuid.UUID) -> list[EmailLabel]:
    rows = await session.execute(
        select(Label.id, Label.name, Label.display_name, EmailLabelRow.filter_id)
        .join(EmailLabelRow, EmailLabelRow.label_id == Label.id)
        .where(EmailLabelRow.email_id == email_id)
        .order_by(Label.display_name)
    )
    return [
        EmailLabel(id=label_id, name=name, display_name=display_name, filter_id=filter_id)
        for label_id, name, display_name, filter_id in rows
    ]


class DocumentLoader:
    """Loads documents for one worker task: from Redis when another processor already built it, else
    from the mailbox. The cache is only an optimisation; anything missing is rebuilt."""

    def __init__(self, redis: Redis, open_source: Callable[[Inbox], MailSource]):
        self._redis = redis
        self._open_source = open_source

    async def load(self, session: AsyncSession, email: Email, inbox: Inbox) -> EmailDocument:
        source = self._open_source(inbox)
        cached = await self._get(_key(email.id))
        doc: EmailDocument | None = None
        if cached is not None:
            try:
                doc = EmailDocument.model_validate_json(decrypt(cached))
                if doc.schema_version != EmailDocument.SCHEMA_VERSION:
                    doc = None
            except (InvalidToken, ValueError):
                doc = None
        if doc is None:
            fetched = await source.fetch(email.provider_message_id)
            doc = build_document(email, inbox, fetched, await email_labels(session, email.id))
            await self._set(_key(email.id), encrypt(doc.model_dump_json()))

        async def read(attachment: Attachment) -> bytes:
            key = f"{_key(email.id)}:att:{hashlib.sha256((attachment.ref or '').encode()).hexdigest()[:16]}"
            if (hit := await self._get(key)) is not None:
                try:
                    return decrypt_bytes(hit)
                except InvalidToken:
                    pass
            data = await source.fetch_attachment(email.provider_message_id, attachment.ref or "")
            if len(data) <= ATTACHMENT_CACHE_MAX_BYTES:
                await self._set(key, encrypt_bytes(data))
            return data

        return doc.bind(read)

    async def _get(self, key: str) -> str | None:
        try:
            return await self._redis.get(key)
        except Exception as exc:  # Redis down: fall back to the mailbox
            logger.warning("Document cache unavailable: %r", exc)
            return None

    async def _set(self, key: str, value: str) -> None:
        try:
            await self._redis.set(key, value, ex=DOCUMENT_TTL)
        except Exception as exc:
            logger.warning("Document cache unavailable: %r", exc)
