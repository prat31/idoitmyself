"""Processors: CRUD, their runs, queuing runs on emails already labelled, and the inputs they ask
the user for. Running them is app.services.processor_engine; the kinds are app.processors."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt
from app.mail.sources import message_url
from app.models.email import Email, EmailLabel
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.processor import (
    ACTIVE_RUN_STATUSES,
    InputValue,
    Processor,
    ProcessorRun,
    ProcessorRunStatus,
    ProcessorStatus,
    Record,
)
from app.processors import kinds
from app.processors.kinds import ProcessorKind
from app.schemas.processor import (
    InputSave,
    ProcessorCreate,
    ProcessorKindRead,
    ProcessorLabel,
    ProcessorRead,
    ProcessorRunCounts,
    ProcessorRunPage,
    ProcessorRunRead,
    ProcessorUpdate,
)
from app.services.datasets import datasets

# A run queued again: as if new.
REQUEUED = {
    "status": ProcessorRunStatus.QUEUED,
    "error": None,
    "attempts": 0,
    "finished_at": None,
    "updated_at": func.now(),
}


class ProcessorInputError(Exception):
    """An unknown label or kind, or invalid settings. Safe to show."""


class DefaultProcessorError(Exception):
    """Built-in default processors can't be deleted (only deactivated)."""


def kind_list() -> list[ProcessorKindRead]:
    all_datasets = {d.name: d for d in datasets()}
    return [
        ProcessorKindRead(
            key=kind.key,
            name=kind.name,
            description=kind.description,
            version=kind.version,
            writes=[all_datasets[record.__dataset__.name] for record in kind.writes],
            config_schema=kind.config.model_json_schema() if kind.config else None,
            has_dashboard=kind.dashboard is not None,
        )
        for kind in sorted(kinds().values(), key=lambda k: k.name)
    ]


def _validate_config(kind: ProcessorKind, config: dict[str, Any]) -> dict[str, Any]:
    if kind.config is None:
        if config:
            raise ProcessorInputError(f"{kind.name} has no settings")
        return {}
    try:
        return kind.config.model_validate(config).model_dump(mode="json")
    except ValidationError as exc:
        raise ProcessorInputError(f"Invalid settings: {exc.errors()[0]['msg']}") from None


async def _labels(session: AsyncSession, label_ids: list[uuid.UUID]) -> list[Label]:
    labels = list(await session.scalars(select(Label).where(Label.id.in_(label_ids))))
    if len(labels) != len(set(label_ids)):
        raise ProcessorInputError("Unknown label")
    return labels


async def _counts(
    session: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[ProcessorRunCounts, datetime | None, int]]:
    rows = await session.execute(
        select(
            ProcessorRun.processor_id, ProcessorRun.status, func.count(), func.max(ProcessorRun.created_at)
        )
        .where(ProcessorRun.processor_id.in_(ids))
        .group_by(ProcessorRun.processor_id, ProcessorRun.status)
    )
    raw: dict[uuid.UUID, dict[ProcessorRunStatus, int]] = {i: {} for i in ids}
    last: dict[uuid.UUID, datetime | None] = {i: None for i in ids}
    for processor_id, status, count, latest in rows:
        raw[processor_id][status] = count
        last[processor_id] = max(filter(None, (last[processor_id], latest)), default=None)
    records = dict(
        (
            await session.execute(
                select(Record.processor_id, func.count())
                .where(Record.processor_id.in_(ids))
                .group_by(Record.processor_id)
            )
        ).all()
    )
    return {
        i: (
            ProcessorRunCounts(
                active=sum(raw[i].get(s, 0) for s in ACTIVE_RUN_STATUSES),
                succeeded=raw[i].get(ProcessorRunStatus.SUCCEEDED, 0),
                skipped=raw[i].get(ProcessorRunStatus.SKIPPED, 0),
                failed=raw[i].get(ProcessorRunStatus.FAILED, 0),
                needs_input=raw[i].get(ProcessorRunStatus.NEEDS_INPUT, 0),
            ),
            last[i],
            records.get(i, 0),
        )
        for i in ids
    }


def _to_read(
    processor: Processor, counts: ProcessorRunCounts, last_run_at: datetime | None, records: int
) -> ProcessorRead:
    kind = kinds().get(processor.kind)
    return ProcessorRead(
        id=processor.id,
        name=processor.name,
        description=processor.description,
        labels=[
            ProcessorLabel(id=label.id, display_name=label.display_name, color=label.color)
            for label in processor.labels
        ],
        kind=processor.kind,
        kind_name=kind.name if kind else processor.kind,
        config=processor.config,
        status=processor.status,
        status_changed_at=processor.status_changed_at,
        created_at=processor.created_at,
        runs=counts,
        last_run_at=last_run_at,
        records=records,
        has_dashboard=bool(kind and kind.dashboard),
        is_default=processor.default_key is not None,
    )


async def list_processors(session: AsyncSession) -> list[ProcessorRead]:
    processors = list(await session.scalars(select(Processor).order_by(Processor.name)))
    counts = await _counts(session, [p.id for p in processors])
    return [_to_read(p, *counts[p.id]) for p in processors]


async def get_processor(session: AsyncSession, processor_id: uuid.UUID) -> ProcessorRead | None:
    processor = await session.get(Processor, processor_id)
    if processor is None:
        return None
    return _to_read(processor, *(await _counts(session, [processor.id]))[processor.id])


async def create_processor(session: AsyncSession, data: ProcessorCreate) -> ProcessorRead:
    kind = kinds().get(data.kind)
    if kind is None:
        raise ProcessorInputError(f"Unknown processor kind {data.kind!r}")
    processor = Processor(
        name=data.name,
        description=data.description or None,
        kind=data.kind,
        config=_validate_config(kind, data.config),
        status=ProcessorStatus.ACTIVE,
        labels=await _labels(session, data.label_ids),
    )
    session.add(processor)
    await session.commit()
    session.expunge(processor)
    return await get_processor(session, processor.id)  # type: ignore[return-value]


async def update_processor(
    session: AsyncSession, processor_id: uuid.UUID, data: ProcessorUpdate
) -> ProcessorRead | None:
    processor = await session.get(Processor, processor_id)
    if processor is None:
        return None
    fields = data.model_fields_set
    if "name" in fields and data.name:
        processor.name = data.name
    if "description" in fields:
        processor.description = data.description or None
    if "label_ids" in fields and data.label_ids:
        processor.labels = await _labels(session, data.label_ids)
    if "config" in fields and data.config is not None:
        kind = kinds().get(processor.kind)
        if kind is None:
            raise ProcessorInputError(f"Unknown processor kind {processor.kind!r}")
        processor.config = _validate_config(kind, data.config)
    if data.status is not None and data.status != processor.status:
        processor.status = data.status
        processor.status_changed_at = datetime.now(UTC)
    await session.commit()
    session.expunge(processor)
    return await get_processor(session, processor_id)


async def delete_processor(session: AsyncSession, processor_id: uuid.UUID) -> bool:
    """Delete a processor. Its records, runs and delivered actions stay (detached from it); runs not
    finished are cancelled. Built-in defaults can't be deleted."""
    processor = await session.get(Processor, processor_id)
    if processor is None:
        return False
    if processor.default_key is not None:
        raise DefaultProcessorError(processor.name)
    await session.execute(
        update(ProcessorRun)
        .where(
            ProcessorRun.processor_id == processor_id,
            ProcessorRun.status.in_((*ACTIVE_RUN_STATUSES, ProcessorRunStatus.NEEDS_INPUT)),
        )
        .values(
            status=ProcessorRunStatus.CANCELLED, error="The processor was deleted", finished_at=func.now()
        )
    )
    await session.delete(processor)
    await session.commit()
    return True


async def list_runs(
    session: AsyncSession,
    processor_id: uuid.UUID,
    page: int,
    page_size: int,
    statuses: list[ProcessorRunStatus] | None,
) -> ProcessorRunPage:
    """The processor's runs, most recently changed first; optionally only some statuses."""
    where = [ProcessorRun.processor_id == processor_id]
    if statuses:
        where.append(ProcessorRun.status.in_(statuses))
    total = await session.scalar(select(func.count()).select_from(ProcessorRun).where(*where))
    rows = await session.execute(
        select(ProcessorRun, Email, Inbox)
        .join(Email, Email.id == ProcessorRun.email_id)
        .join(Inbox, Inbox.id == Email.inbox_id)
        .where(*where)
        .order_by(ProcessorRun.updated_at.desc(), ProcessorRun.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ProcessorRunPage(
        items=[
            ProcessorRunRead(
                id=run.id,
                status=run.status,
                error=run.error,
                attempts=run.attempts,
                records_written=run.records_written,
                input_name=run.input_name,
                input_scope=run.input_scope,
                input_prompt=run.input_prompt,
                created_at=run.created_at,
                finished_at=run.finished_at,
                email_id=email.id,
                sent_at=email.sent_at,
                from_address=email.from_address,
                subject=email.subject,
                inbox_name=inbox.name,
                open_url=message_url(inbox.provider, inbox.email_address, email.provider_message_id),
            )
            for run, email, inbox in rows
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def queue_existing(session: AsyncSession, processor_id: uuid.UUID) -> list[uuid.UUID] | None:
    """Queue runs on the emails that already carry any of the processor's labels and have never been
    run through it. None if the processor doesn't exist."""
    processor = await session.get(Processor, processor_id)
    if processor is None:
        return None
    rows = await session.execute(
        select(EmailLabel.email_id, func.array_agg(EmailLabel.label_id))
        .where(
            EmailLabel.label_id.in_([label.id for label in processor.labels]),
            ~exists().where(
                ProcessorRun.processor_id == processor_id, ProcessorRun.email_id == EmailLabel.email_id
            ),
        )
        .group_by(EmailLabel.email_id)
    )
    values = [
        {
            "id": uuid.uuid4(),
            "processor_id": processor_id,
            "email_id": email_id,
            "trigger_label_ids": trigger_ids,
            "status": ProcessorRunStatus.QUEUED,
        }
        for email_id, trigger_ids in rows
    ]
    ids: list[uuid.UUID] = []
    if values:
        ids = list(
            await session.scalars(
                insert(ProcessorRun)
                .values(values)
                .on_conflict_do_nothing(constraint="uq_processor_runs_processor_id")
                .returning(ProcessorRun.id)
            )
        )
    await session.commit()
    return ids


async def requeue(
    session: AsyncSession, processor_id: uuid.UUID, statuses: list[ProcessorRunStatus]
) -> list[uuid.UUID]:
    """Queue the processor's runs in these statuses again (e.g. failed ones after a fix, or finished
    ones after the kind's code changed). Re-runs replace what they wrote before."""
    ids = list(
        await session.scalars(
            update(ProcessorRun)
            .where(ProcessorRun.processor_id == processor_id, ProcessorRun.status.in_(statuses))
            .values(**REQUEUED)
            .returning(ProcessorRun.id)
        )
    )
    await session.commit()
    return ids


async def save_input(session: AsyncSession, data: InputSave) -> list[uuid.UUID]:
    """Save (or replace) an input, and queue again every run waiting for it. Returns those runs."""
    secret = encrypt(data.value)
    await session.execute(
        insert(InputValue)
        .values(id=uuid.uuid4(), name=data.name, scope=data.scope, encrypted_value=secret)
        .on_conflict_do_update(
            constraint="uq_input_values_name", set_={"encrypted_value": secret, "updated_at": func.now()}
        )
    )
    ids = list(
        await session.scalars(
            update(ProcessorRun)
            .where(
                ProcessorRun.status == ProcessorRunStatus.NEEDS_INPUT,
                ProcessorRun.input_name == data.name,
                ProcessorRun.input_scope == data.scope,
            )
            .values(**REQUEUED)
            .returning(ProcessorRun.id)
        )
    )
    await session.commit()
    return ids
