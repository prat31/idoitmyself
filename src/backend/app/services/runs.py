import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.email import Email, LabelEvaluation, condition_hash
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.run import Run, RunInbox, RunKind, RunLabel, RunStatus
from app.schemas.run import AdhocRunCreate, CoveredRange, LabelCoverage, RunCoverage, RunCoverageRequest

logger = logging.getLogger(__name__)


class RunRequestError(Exception):
    """The run request references missing or unusable labels/inboxes. Message is user-facing."""


async def list_runs(session: AsyncSession, limit: int = 100) -> list[Run]:
    result = await session.scalars(select(Run).order_by(Run.created_at.desc()).limit(limit))
    return list(result)


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> Run | None:
    return await session.get(Run, run_id)


async def create_adhoc_run(session: AsyncSession, data: AdhocRunCreate) -> Run:
    labels = {
        label.id: label for label in await session.scalars(select(Label).where(Label.id.in_(data.label_ids)))
    }
    inboxes = {
        inbox.id: inbox for inbox in await session.scalars(select(Inbox).where(Inbox.id.in_(data.inbox_ids)))
    }
    if missing := [str(i) for i in data.label_ids if i not in labels]:
        raise RunRequestError(f"Unknown labels: {', '.join(missing)}")
    if missing := [str(i) for i in data.inbox_ids if i not in inboxes]:
        raise RunRequestError(f"Unknown inboxes: {', '.join(missing)}")
    if without := [labels[i].name for i in data.label_ids if not labels[i].filter_condition]:
        raise RunRequestError(
            f"Labels without a filter condition can't be used in a run: {', '.join(without)}"
        )

    run = Run(
        name=data.name,
        kind=RunKind.ADHOC,
        reclassify=data.reclassify,
        status=RunStatus.QUEUED,
        window_start=data.window_start,
        window_end=data.window_end,
        model=get_settings().jev_model,
        labels=[
            RunLabel(
                position=position,
                label_id=label.id,
                label_name=label.name,
                filter_condition=label.filter_condition or "",
                match_threshold=label.match_threshold,
            )
            for position, label in enumerate(labels[i] for i in data.label_ids)
        ],
        inboxes=[
            RunInbox(
                position=position, inbox_id=inbox.id, inbox_name=inbox.name, email_address=inbox.email_address
            )
            for position, inbox in enumerate(inboxes[i] for i in data.inbox_ids)
        ],
    )
    session.add(run)
    await session.commit()

    try:
        await asyncio.to_thread(_enqueue, run.id)
    except Exception as exc:  # broker unreachable: don't leave a run queued forever
        logger.exception("Could not enqueue run %s", run.id)
        run.status = RunStatus.FAILED
        run.error = f"Could not queue the run: {exc}"
        await session.commit()
    await session.refresh(run)
    return run


def _enqueue(run_id: uuid.UUID) -> None:
    from app.worker import EXECUTE_RUN_TASK, celery_app

    celery_app.send_task(EXECUTE_RUN_TASK, args=[str(run_id)])


async def coverage(session: AsyncSession, data: RunCoverageRequest) -> RunCoverage:
    """For each label: which parts of the window earlier completed runs already covered, for every
    selected inbox, with the label's current filter condition — and how many stored emails in the
    window already have an answer for it. Drives the "already scanned" notice in the New run form."""
    labels = list(
        await session.scalars(select(Label).where(Label.id.in_(data.label_ids)).order_by(Label.name))
    )
    inbox_ids = set(data.inbox_ids)
    result: list[LabelCoverage] = []
    for label in labels:
        if not label.filter_condition:
            continue
        # Completed runs that asked this label with the same condition, and the inboxes each covered.
        rows = await session.execute(
            select(Run.window_start, Run.window_end, RunInbox.inbox_id)
            .join(RunLabel, RunLabel.run_id == Run.id)
            .join(RunInbox, RunInbox.run_id == Run.id)
            .where(
                Run.status == RunStatus.COMPLETED,
                RunLabel.label_id == label.id,
                RunLabel.filter_condition == label.filter_condition,
                RunInbox.inbox_id.in_(inbox_ids),
                RunInbox.error.is_(None),
                Run.window_end > data.window_start,
                Run.window_start < data.window_end,
            )
        )
        per_inbox: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
        for start, end, inbox_id in rows:
            per_inbox.setdefault(inbox_id, []).append(
                (max(start, data.window_start), min(end, data.window_end))
            )
        # A range counts as covered only if it is covered in every selected inbox.
        covered = (
            intersect_all([merge_ranges(per_inbox.get(inbox_id, [])) for inbox_id in inbox_ids])
            if inbox_ids
            else []
        )
        evaluated = await session.scalar(
            select(func.count())
            .select_from(LabelEvaluation)
            .join(Email, Email.id == LabelEvaluation.email_id)
            .where(
                LabelEvaluation.label_id == label.id,
                LabelEvaluation.condition_hash == condition_hash(label.filter_condition),
                Email.inbox_id.in_(inbox_ids),
                Email.sent_at >= data.window_start,
                Email.sent_at < data.window_end,
            )
        )
        result.append(
            LabelCoverage(
                label_id=label.id,
                label_name=label.name,
                covered=[CoveredRange(start=s, end=e) for s, e in covered],
                evaluated_emails=evaluated or 0,
            )
        )
    return RunCoverage(labels=result)


def merge_ranges(ranges: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def intersect_all(range_sets: list[list[tuple[datetime, datetime]]]) -> list[tuple[datetime, datetime]]:
    if not range_sets:
        return []
    current = range_sets[0]
    for other in range_sets[1:]:
        result = []
        i = j = 0
        while i < len(current) and j < len(other):
            start = max(current[i][0], other[j][0])
            end = min(current[i][1], other[j][1])
            if start < end:
                result.append((start, end))
            if current[i][1] < other[j][1]:
                i += 1
            else:
                j += 1
        current = result
    return current
