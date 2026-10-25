from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import encrypt
from app.models.inbox import Inbox, InboxCredential, InboxProvider
from app.models.scan import InboxSync, Scan
from app.schemas.inbox import InboxDraft, InboxLatestScan, InboxRead, TagRead
from app.services.filters import active_filters
from app.services.gmail_oauth import GoogleTokens
from app.services.tags import get_or_create_tags


async def list_inboxes(session: AsyncSession) -> list[InboxRead]:
    inboxes = list(await session.scalars(select(Inbox).order_by(Inbox.created_at)))
    active = await active_filters(session)
    scanned_until = dict((await session.execute(select(InboxSync.inbox_id, InboxSync.scanned_until))).all())
    latest = select(Scan).distinct(Scan.inbox_id).order_by(Scan.inbox_id, Scan.created_at.desc())
    last_scans = {scan.inbox_id: scan for scan in await session.scalars(latest)}
    return [
        InboxRead(
            id=inbox.id,
            provider=inbox.provider,
            name=inbox.name,
            email_address=inbox.email_address,
            notes=inbox.notes,
            tags=[TagRead.model_validate(tag) for tag in inbox.tags],
            connected_at=inbox.connected_at,
            created_at=inbox.created_at,
            active_filters=sum(1 for f in active if f.covers(inbox)),
            scanned_until=scanned_until.get(inbox.id),
            last_scan=InboxLatestScan.model_validate(last_scans[inbox.id], from_attributes=True)
            if inbox.id in last_scans
            else None,
        )
        for inbox in inboxes
    ]


async def save_gmail_inbox(
    session: AsyncSession, draft: InboxDraft, email_address: str, tokens: GoogleTokens
) -> tuple[Inbox, bool]:
    """Create the inbox, or — if this Gmail account is already connected — update it with the new
    details and credentials. Returns (inbox, created)."""
    # Resolve tags before touching the inbox: on an async session, assigning a relationship on an
    # already-flushed object would trigger a lazy load.
    tags = await get_or_create_tags(session, draft.tags)
    inbox = await session.scalar(
        select(Inbox)
        .where(Inbox.provider == InboxProvider.GMAIL, Inbox.email_address == email_address)
        .options(selectinload(Inbox.credential))
    )
    created = inbox is None

    if inbox is None:
        inbox = Inbox(provider=InboxProvider.GMAIL, email_address=email_address, credential=InboxCredential())
        session.add(inbox)

    inbox.name = draft.name
    inbox.notes = draft.notes
    inbox.connected_at = datetime.now(UTC)
    inbox.tags = tags

    credential = inbox.credential
    credential.encrypted_refresh_token = encrypt(tokens.refresh_token)
    credential.encrypted_access_token = encrypt(tokens.access_token)
    credential.access_token_expires_at = tokens.expires_at
    credential.scopes = tokens.scopes

    await session.commit()
    return inbox, created
