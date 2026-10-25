from collections.abc import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.mail import gmail
from app.mail.gmail import GmailSource
from app.mail.types import MailSource
from app.models.inbox import Inbox, InboxProvider


def open_mail_source(
    inbox: Inbox, client: httpx.AsyncClient, session_factory: Callable[[], AsyncSession]
) -> MailSource:
    """The MailSource for an inbox's provider. The only place run logic touches provider specifics."""
    match inbox.provider:
        case InboxProvider.GMAIL:
            return GmailSource(inbox.id, client, session_factory)
    raise ValueError(f"Unsupported provider: {inbox.provider}")


def message_url(provider: InboxProvider, email_address: str, message_id: str) -> str | None:
    """A link that opens the message in the provider's own web UI, or None if it has none."""
    match provider:
        case InboxProvider.GMAIL:
            return gmail.web_url(email_address, message_id)
    return None
