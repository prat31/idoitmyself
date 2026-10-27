"""Delivering the actions processors ask for (app.processors.actions), each at most once.

The `processors.deliver_action` task delivers one when due; the actions tick (beat) hands over the
scheduled ones whose time has come, and any left undelivered for long. Notify actions create an in-app
notification (once: it's unique per action) and, when Telegram is configured, send it there once."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import ValidationError
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.retry import TransientError
from app.mail.sources import message_url
from app.models.email import Email
from app.models.inbox import Inbox
from app.models.processor import Action, ActionStatus, Notification
from app.processors.actions import ACTION_TYPES, Notify
from app.services import telegram

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]

# A dispatched action not done after this long is handed over again (its message was lost).
REDISPATCH_AFTER = timedelta(minutes=10)


async def due_actions(session_factory: SessionFactory, now: datetime | None = None) -> list[uuid.UUID]:
    """Pending actions whose time has come and that aren't being delivered, marked dispatched."""
    now = now or datetime.now(UTC)
    async with session_factory() as session:
        ids = list(
            await session.scalars(
                update(Action)
                .where(
                    Action.status == ActionStatus.PENDING,
                    Action.run_at <= now,
                    or_(Action.dispatched_at.is_(None), Action.dispatched_at < now - REDISPATCH_AFTER),
                )
                .values(dispatched_at=now)
                .returning(Action.id)
            )
        )
        await session.commit()
    return ids


async def email_link(session: AsyncSession, email_id: uuid.UUID | None) -> str | None:
    if email_id is None:
        return None
    row = (
        await session.execute(
            select(Email.provider_message_id, Inbox.provider, Inbox.email_address)
            .join(Inbox, Inbox.id == Email.inbox_id)
            .where(Email.id == email_id)
        )
    ).first()
    return message_url(row[1], row[2], row[0]) if row else None


async def deliver(
    action_id: uuid.UUID, *, final_attempt: bool, session_factory: SessionFactory, client: httpx.AsyncClient
) -> None:
    """Deliver one action. Raises TransientError when it should be retried later."""
    async with session_factory() as session:
        action = await session.get(Action, action_id)
        if action is None or action.status != ActionStatus.PENDING:
            return
        action.attempts += 1
        action.dispatched_at = datetime.now(UTC)
        await session.commit()
        action_type = ACTION_TYPES.get(action.type)
        try:
            if action_type is None:
                raise ValueError(f"Unknown action type {action.type!r}")
            payload = action_type.model_validate(action.payload)
        except (ValueError, ValidationError) as exc:
            await _finish(session, action, ActionStatus.FAILED, str(exc))
            return
        note: str | None = None
        if isinstance(payload, Notify):
            note = await _notify(session, action, payload, client, final_attempt)
        await _finish(session, action, ActionStatus.DONE, note)


async def _notify(
    session: AsyncSession, action: Action, payload: Notify, client: httpx.AsyncClient, final_attempt: bool
) -> str | None:
    """Create the in-app notification (once) and send it to Telegram (once). Returns a note on a
    Telegram problem that retrying won't fix; the in-app notification is there regardless."""
    await session.execute(
        insert(Notification)
        .values(
            id=uuid.uuid4(),
            action_id=action.id,
            processor_id=action.processor_id,
            email_id=action.email_id,
            title=payload.title,
            body=payload.body,
        )
        .on_conflict_do_nothing(index_elements=[Notification.action_id])
    )
    await session.commit()
    notification = await session.scalar(select(Notification).where(Notification.action_id == action.id))
    if notification is None or notification.telegram_sent_at is not None or not telegram.is_configured():
        return None
    text = telegram.format_message(payload.title, payload.body, await email_link(session, action.email_id))
    try:
        await telegram.send_message(client, text)
    except TransientError as exc:
        if not final_attempt:
            raise
        logger.warning("Action %s: gave up on Telegram: %s", action.id, exc)
        return f"Not sent to Telegram: {exc}"
    except telegram.TelegramError as exc:
        logger.warning("Action %s: Telegram refused it: %s", action.id, exc)
        return f"Not sent to Telegram: {exc}"
    notification.telegram_sent_at = datetime.now(UTC)
    await session.commit()
    return None


async def _finish(session: AsyncSession, action: Action, status: ActionStatus, error: str | None) -> None:
    action.status = status
    action.error = error[:2000] if error else None
    action.done_at = datetime.now(UTC)
    await session.commit()
