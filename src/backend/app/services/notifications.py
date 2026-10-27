"""In-app notifications (created by Notify actions, see app.services.actions)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.mail.sources import message_url
from app.models.email import Email
from app.models.inbox import Inbox
from app.models.processor import Notification, Processor
from app.schemas.notification import NotificationPage, NotificationRead


async def list_notifications(
    session: AsyncSession, *, page: int, page_size: int, unread_only: bool
) -> NotificationPage:
    """Newest first, leaving out dismissed ones."""
    shown = Notification.dismissed_at.is_(None)
    where = [shown, Notification.read_at.is_(None)] if unread_only else [shown]
    total = await session.scalar(select(func.count()).select_from(Notification).where(*where)) or 0
    unread = (
        await session.scalar(
            select(func.count()).select_from(Notification).where(shown, Notification.read_at.is_(None))
        )
        or 0
    )
    rows = await session.execute(
        select(Notification, Processor.name, Email.provider_message_id, Inbox.provider, Inbox.email_address)
        .outerjoin(Processor, Processor.id == Notification.processor_id)
        .outerjoin(Email, Email.id == Notification.email_id)
        .outerjoin(Inbox, Inbox.id == Email.inbox_id)
        .where(*where)
        .order_by(Notification.created_at.desc(), Notification.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return NotificationPage(
        items=[
            NotificationRead(
                id=n.id,
                title=n.title,
                body=n.body,
                created_at=n.created_at,
                read_at=n.read_at,
                processor_id=n.processor_id,
                processor_name=processor_name,
                open_url=message_url(provider, address, message_id) if message_id else None,
            )
            for n, processor_name, message_id, provider, address in rows
        ],
        total=total,
        unread=unread,
        page=page,
        page_size=page_size,
    )


async def mark_read(session: AsyncSession, notification_id: uuid.UUID, read: bool) -> bool:
    result = await session.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(read_at=datetime.now(UTC) if read else None)
    )
    await session.commit()
    return bool(result.rowcount)


async def mark_all_read(session: AsyncSession) -> int:
    result = await session.execute(
        update(Notification).where(Notification.read_at.is_(None)).values(read_at=datetime.now(UTC))
    )
    await session.commit()
    return result.rowcount or 0


async def dismiss(session: AsyncSession, notification_id: uuid.UUID) -> bool:
    """Remove it from the list (it's also read from then on)."""
    now = datetime.now(UTC)
    notification = await session.get(Notification, notification_id)
    if notification is None:
        return False
    notification.dismissed_at = now
    notification.read_at = notification.read_at or now
    await session.commit()
    return True
