"""Runs processors on emails. A run is one processor on one email (a Celery task on the `processors`
queue, see app/worker.py):

- Runs are created as `queued` when a scan adds labels to an email (in the same transaction, see
  `create_runs`): one per active processor with any of those labels, never two for the same processor
  and email. Or on request, for emails already labelled. The sweep re-publishes runs whose message was
  lost; with acks_late a run can also be delivered twice, which is safe because runs are idempotent.
- `run_processor` loads the email's EmailDocument (Redis cache or the mailbox), calls the kind's
  `process`, then, in one transaction, replaces the processor's records for the email and saves the
  actions it asked for (a delivered action is never redone).
- A run that needs user input waits as `needs_input`; saving the input queues it again.
- Transient failures come back as a RunRetry for the task to re-publish with a delay: workers never
  sleep to retry. Nothing here is sent to any AI."""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt
from app.core.quota import QuotaExhausted
from app.core.redis import loop_redis
from app.core.retry import TransientError
from app.mail.sources import open_mail_source
from app.mail.types import MailSource, MailSourceError
from app.models.email import Email
from app.models.inbox import Inbox
from app.models.processor import (
    ACTIVE_RUN_STATUSES,
    Action,
    ActionStatus,
    InputValue,
    Notification,
    Processor,
    ProcessorRun,
    ProcessorRunStatus,
    ProcessorStatus,
    Record,
    processor_labels,
)
from app.processors import kinds
from app.processors.context import Context
from app.processors.loader import DocumentLoader
from app.processors.outcomes import Fail, NeedsInput, Retry, Skip

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]
OpenSourceFn = Callable[[Inbox, httpx.AsyncClient, SessionFactory], MailSource]


@dataclass(frozen=True)
class RunRetry:
    """The run couldn't finish now and is queued again: re-publish it after a delay. `paced` means our
    own quota budget held it back, which doesn't use an attempt."""

    attempt: int
    retry_after: float | None
    paced: bool


@dataclass
class RunOutcome:
    retry: RunRetry | None = None
    # Actions due now, to publish (later ones are picked up by the actions tick).
    due_actions: list[uuid.UUID] = field(default_factory=list)


async def create_runs(
    session: AsyncSession, email_id: uuid.UUID, label_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Queue a run of every active processor with any of these labels (just added to the email). A
    processor that already has a run for the email gets none. Part of the caller's transaction; the
    caller publishes the returned ids after committing."""
    if not label_ids:
        return []
    rows = await session.execute(
        select(processor_labels.c.processor_id, processor_labels.c.label_id)
        .join(Processor, Processor.id == processor_labels.c.processor_id)
        .where(processor_labels.c.label_id.in_(label_ids), Processor.status == ProcessorStatus.ACTIVE)
    )
    triggers: dict[uuid.UUID, list[uuid.UUID]] = {}
    for processor_id, label_id in rows:
        triggers.setdefault(processor_id, []).append(label_id)
    if not triggers:
        return []
    created = await session.scalars(
        insert(ProcessorRun)
        .values(
            [
                {
                    "id": uuid.uuid4(),
                    "processor_id": processor_id,
                    "email_id": email_id,
                    "trigger_label_ids": label_ids_,
                    "status": ProcessorRunStatus.QUEUED,
                }
                for processor_id, label_ids_ in triggers.items()
            ]
        )
        .on_conflict_do_nothing(constraint="uq_processor_runs_processor_id")
        .returning(ProcessorRun.id)
    )
    return list(created)


def _secret_lookup(session_factory: SessionFactory):
    async def lookup(name: str, scope: str) -> str | None:
        async with session_factory() as session:
            value = await session.scalar(
                select(InputValue.encrypted_value).where(InputValue.name == name, InputValue.scope == scope)
            )
        return decrypt(value) if value else None

    return lookup


async def run_processor(
    run_id: uuid.UUID,
    *,
    max_attempts: int,
    session_factory: SessionFactory,
    client: httpx.AsyncClient,
    open_source: OpenSourceFn = open_mail_source,
) -> RunOutcome:
    """Run one processor on one email."""
    async with session_factory() as session:
        run = await session.get(ProcessorRun, run_id)
        if run is None or run.status not in ACTIVE_RUN_STATUSES:
            return RunOutcome()  # finished meanwhile, or waiting for input
        processor = await session.get(Processor, run.processor_id) if run.processor_id else None
        if processor is None:
            await _finish(session, run, ProcessorRunStatus.CANCELLED, "The processor was deleted")
            return RunOutcome()
        email = await session.get(Email, run.email_id)
        inbox = await session.get(Inbox, email.inbox_id) if email else None
        if email is None or inbox is None:
            await _finish(session, run, ProcessorRunStatus.FAILED, "The email or its inbox no longer exists")
            return RunOutcome()
        kind = kinds().get(processor.kind)
        if kind is None:
            await _finish(
                session, run, ProcessorRunStatus.FAILED, f"Unknown processor kind {processor.kind!r}"
            )
            return RunOutcome()
        try:
            config = kind.config.model_validate(processor.config) if kind.config else None
        except ValidationError as exc:
            await _finish(session, run, ProcessorRunStatus.FAILED, f"Invalid processor settings: {exc}")
            return RunOutcome()
        run.status = ProcessorRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        run.kind_version = kind.version
        attempts, trigger_ids, processor_name = run.attempts, set(run.trigger_label_ids), processor.name
        await session.commit()

        loader = DocumentLoader(loop_redis(), lambda i: open_source(i, client, session_factory))
        try:
            doc = await loader.load(session, email, inbox)
            ctx = Context(
                processor_id=processor.id,
                processor_name=processor_name,
                config=config,
                trigger_labels=[label for label in doc.labels if label.id in trigger_ids],
                secrets=_secret_lookup(session_factory),
                allowed=kind.writes,
            )
            await kind.process(doc, ctx)
        except QuotaExhausted as exc:
            await _requeue(session_factory, run_id, attempts)
            return RunOutcome(retry=RunRetry(attempt=attempts, retry_after=exc.retry_after, paced=True))
        except (TransientError, Retry) as exc:
            after = exc.retry_after if isinstance(exc, TransientError) else exc.after
            if attempts + 1 >= max_attempts:
                message = f"Gave up after {attempts + 1} attempts: {exc}"
                await _finish_by_id(session_factory, run_id, ProcessorRunStatus.FAILED, message)
                return RunOutcome()
            logger.warning(
                "Processor run %s deferred (attempt %s/%s): %s", run_id, attempts + 1, max_attempts, exc
            )
            await _requeue(session_factory, run_id, attempts + 1)
            return RunOutcome(retry=RunRetry(attempt=attempts, retry_after=after, paced=False))
        except NeedsInput as exc:
            await _needs_input(session_factory, run_id, exc)
            return RunOutcome()
        except Skip as exc:
            await _finish_by_id(session_factory, run_id, ProcessorRunStatus.SKIPPED, str(exc))
            return RunOutcome()
        except (Fail, MailSourceError) as exc:
            await _finish_by_id(session_factory, run_id, ProcessorRunStatus.FAILED, str(exc))
            return RunOutcome()
        except Exception as exc:  # anything else fails this run, never the worker
            logger.exception("Processor run %s failed", run_id)
            await _finish_by_id(session_factory, run_id, ProcessorRunStatus.FAILED, repr(exc))
            return RunOutcome()

    return RunOutcome(due_actions=await _save(session_factory, run_id, processor.id, email.id, ctx))


async def _save(
    session_factory: SessionFactory,
    run_id: uuid.UUID,
    processor_id: uuid.UUID,
    email_id: uuid.UUID,
    ctx: Context,
) -> list[uuid.UUID]:
    """Replace the processor's records for the email and save its actions: one transaction."""
    now = datetime.now(UTC)
    due: list[uuid.UUID] = []
    async with session_factory() as session:
        await session.execute(
            delete(Record).where(Record.processor_id == processor_id, Record.email_id == email_id)
        )
        session.add_all(
            Record(
                dataset=record.__dataset__.name,
                schema_version=record.__dataset__.version,
                processor_id=processor_id,
                email_id=email_id,
                run_id=run_id,
                key=record.record_key(),
                occurred_at=record.occurred_at(),
                data=record.model_dump(mode="json"),
            )
            for record in ctx.records
        )
        for planned in ctx.actions:
            values = {
                "type": planned.action.type,
                "payload": planned.action.model_dump(mode="json"),
                "run_at": planned.at or now,
                "run_id": run_id,
                "updated_at": func.now(),
            }
            action_id = await session.scalar(
                insert(Action)
                .values(
                    id=uuid.uuid4(),
                    processor_id=processor_id,
                    email_id=email_id,
                    key=planned.key,
                    status=ActionStatus.PENDING,
                    **values,
                )
                .on_conflict_do_update(
                    constraint="uq_actions_processor_id",
                    set_=values,
                    where=Action.status == ActionStatus.PENDING,  # a delivered action is never redone
                )
                .returning(Action.id)
            )
            if action_id is not None and (planned.at or now) <= now:
                due.append(action_id)
        await session.execute(
            update(ProcessorRun)
            .where(ProcessorRun.id == run_id)
            .values(
                status=ProcessorRunStatus.SUCCEEDED,
                error=None,
                records_written=len(ctx.records),
                input_name=None,
                input_scope=None,
                input_prompt=None,
                finished_at=func.now(),
                updated_at=func.now(),
            )
        )
        await session.commit()
    return due


async def _finish(
    session: AsyncSession, run: ProcessorRun, status: ProcessorRunStatus, error: str | None
) -> None:
    run.status = status
    run.error = error[:2000] if error else None
    run.finished_at = datetime.now(UTC)
    if status == ProcessorRunStatus.FAILED:
        await _notify_failure(session, run)
    await session.commit()


async def _notify_failure(session: AsyncSession, run: ProcessorRun) -> None:
    """An in-app notification (not Telegram) that a processor couldn't process an email it should
    have: the user can open the email, re-run it once fixed, or dismiss the notification. Skipped
    runs (nothing for it to do) don't notify."""
    processor_name = await session.scalar(select(Processor.name).where(Processor.id == run.processor_id))
    subject = await session.scalar(select(Email.subject).where(Email.id == run.email_id))
    email_exists = subject is not None or await session.get(Email, run.email_id) is not None
    session.add(
        Notification(
            processor_id=run.processor_id,
            email_id=run.email_id if email_exists else None,
            title=f"{processor_name or 'A processor'} couldn't process an email",
            body=" · ".join(part for part in (subject, run.error) if part)[:2000] or None,
        )
    )


async def _finish_by_id(
    session_factory: SessionFactory, run_id: uuid.UUID, status: ProcessorRunStatus, error: str | None
) -> None:
    async with session_factory() as session:
        run = await session.get(ProcessorRun, run_id)
        if run is not None:
            await _finish(session, run, status, error)


async def _needs_input(session_factory: SessionFactory, run_id: uuid.UUID, exc: NeedsInput) -> None:
    async with session_factory() as session:
        await session.execute(
            update(ProcessorRun)
            .where(ProcessorRun.id == run_id)
            .values(
                status=ProcessorRunStatus.NEEDS_INPUT,
                error=str(exc),
                input_name=exc.name,
                input_scope=exc.scope,
                input_prompt=exc.prompt,
                finished_at=func.now(),
                updated_at=func.now(),
            )
        )
        await session.commit()


async def _requeue(session_factory: SessionFactory, run_id: uuid.UUID, attempts: int) -> None:
    async with session_factory() as session:
        await session.execute(
            update(ProcessorRun)
            .where(ProcessorRun.id == run_id)
            .values(status=ProcessorRunStatus.QUEUED, attempts=attempts, updated_at=func.now())
        )
        await session.commit()


async def stale_runs(session_factory: SessionFactory, now: datetime | None = None) -> list[uuid.UUID]:
    """Runs queued or running with no progress for PROCESSOR_STALE_MINUTES: their message was lost
    (e.g. the worker was killed). They're queued again, and the caller re-publishes them."""
    now = now or datetime.now(UTC)
    stale_before = now - timedelta(minutes=get_settings().processor_stale_minutes)
    async with session_factory() as session:
        ids = list(
            await session.scalars(
                update(ProcessorRun)
                .where(ProcessorRun.status.in_(ACTIVE_RUN_STATUSES), ProcessorRun.updated_at < stale_before)
                .values(status=ProcessorRunStatus.QUEUED, updated_at=func.now())
                .returning(ProcessorRun.id)
            )
        )
        await session.commit()
    if ids:
        logger.info("Re-queued %s stale processor runs", len(ids))
    return ids
