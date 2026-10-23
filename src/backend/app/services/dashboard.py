"""App-wide dashboard: run/spend summary, attention items, live status, coverage and recent matches.
Everything is derived from stored data (runs, label_evaluations, email_labels) — no provider calls."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import redis_client
from app.models.email import Email, EmailLabel, LabelEvaluation, condition_hash
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.run import Run, RunInbox, RunLabel, RunStatus
from app.schemas.dashboard import (
    AttentionInbox,
    AttentionLabel,
    AttentionRun,
    CoveredSpan,
    DashboardAttention,
    DashboardCoverage,
    DashboardRecent,
    DashboardStatus,
    DashboardSummary,
    InboxStatus,
    LabelCoverageRow,
    LabelMonth,
    RecentMatch,
    SpendBucket,
)
from app.services.runs import intersect_all, merge_ranges
from app.services.stats import choose_granularity, fill_buckets, parse_timezone

NEAR_WINDOW = 0.1
RECENT_PROBLEM_DAYS = 30


async def summary(
    session: AsyncSession, *, start: datetime | None, end: datetime | None, tz_name: str
) -> DashboardSummary:
    tz = parse_timezone(tz_name)
    finished = [Run.finished_at.is_not(None)]
    if start:
        finished.append(Run.finished_at >= start)
    if end:
        finished.append(Run.finished_at < end)

    completed, failed, cost, processed, skipped = (
        await session.execute(
            select(
                func.count().filter(Run.status == RunStatus.COMPLETED),
                func.count().filter(Run.status == RunStatus.FAILED),
                func.coalesce(func.sum(Run.cost_usd), 0),
                func.coalesce(func.sum(Run.emails_processed), 0),
                func.coalesce(func.sum(Run.emails_skipped), 0),
            ).where(*finished)
        )
    ).one()
    sent = int(processed) - int(skipped)
    per_email = Decimal(cost) / sent if sent else Decimal(0)

    # Spend over time, bucketed by run finish time in the viewer's timezone.
    if start and end:
        first, last = start.astimezone(tz).date(), (end - timedelta(microseconds=1)).astimezone(tz).date()
    else:
        bounds = (
            await session.execute(
                select(func.min(Run.finished_at), func.max(Run.finished_at)).where(*finished)
            )
        ).one()
        today = datetime.now(tz).date()
        first = bounds[0].astimezone(tz).date() if bounds[0] else today
        last = bounds[1].astimezone(tz).date() if bounds[1] else today
    granularity = choose_granularity(timedelta(days=(last - first).days + 1))
    bucket = func.date(func.date_trunc(granularity, func.timezone(tz.key, Run.finished_at)))
    rows = await session.execute(
        select(bucket, func.sum(Run.cost_usd), func.sum(Run.emails_processed - Run.emails_skipped))
        .where(*finished)
        .group_by(bucket)
    )
    spent = {row[0]: (Decimal(row[1] or 0), int(row[2] or 0)) for row in rows}
    spend = [
        SpendBucket(
            start=b.start,
            cost_usd=spent.get(b.start, (Decimal(0), 0))[0],
            emails=spent.get(b.start, (0, 0))[1],
        )
        for b in fill_buckets({}, first, last, granularity)
    ]

    # Labels: emails sent this calendar month vs last month (viewer's timezone), all inboxes.
    this_month = datetime.now(tz).date().replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    month = func.date(func.date_trunc("month", func.timezone(tz.key, Email.sent_at)))
    month_rows = await session.execute(
        select(EmailLabel.label_id, month, func.count())
        .join(Email, Email.id == EmailLabel.email_id)
        .where(month.in_([this_month, last_month]))
        .group_by(EmailLabel.label_id, month)
    )
    per_label: dict[uuid.UUID, dict[date, int]] = {}
    for label_id, bucket_month, count in month_rows:
        per_label.setdefault(label_id, {})[bucket_month] = count
    label_months = [
        LabelMonth(
            label_id=label.id,
            name=label.name,
            color=label.color,
            this_month=per_label.get(label.id, {}).get(this_month, 0),
            last_month=per_label.get(label.id, {}).get(last_month, 0),
        )
        for label in await session.scalars(select(Label).order_by(Label.name))
    ]

    return DashboardSummary(
        runs_completed=completed,
        runs_failed=failed,
        cost_usd=Decimal(cost),
        emails_sent_to_model=sent,
        emails_skipped=int(skipped),
        estimated_saved_usd=per_email * int(skipped),
        spend_granularity=granularity,
        spend=spend,
        label_months=label_months,
    )


async def attention(session: AsyncSession) -> DashboardAttention:
    labels = list(await session.scalars(select(Label).order_by(Label.name)))

    def ref(label: Label, count: int | None = None) -> AttentionLabel:
        return AttentionLabel(label_id=label.id, name=label.name, color=label.color, count=count)

    without, stale, never, near, misses = [], [], [], [], []
    for label in labels:
        if not label.filter_condition:
            without.append(ref(label))
            continue
        last_asked = await session.scalar(
            select(RunLabel.filter_condition)
            .join(Run, Run.id == RunLabel.run_id)
            .where(RunLabel.label_id == label.id, Run.status == RunStatus.COMPLETED)
            .order_by(Run.finished_at.desc())
            .limit(1)
        )
        if last_asked is None:
            never.append(ref(label))
        elif last_asked != label.filter_condition:
            stale.append(ref(label))

        current = [
            LabelEvaluation.label_id == label.id,
            LabelEvaluation.condition_hash == condition_hash(label.filter_condition),
        ]
        t = label.match_threshold
        near_count, miss_count = (
            await session.execute(
                select(
                    func.count().filter(func.abs(LabelEvaluation.probability - t) <= NEAR_WINDOW),
                    func.count().filter(
                        LabelEvaluation.probability < t, LabelEvaluation.probability >= t - NEAR_WINDOW
                    ),
                ).where(*current)
            )
        ).one()
        if near_count:
            near.append(ref(label, near_count))
        if miss_count:
            misses.append(ref(label, miss_count))

    since = datetime.now(UTC) - timedelta(days=RECENT_PROBLEM_DAYS)
    problem_runs = await session.scalars(
        select(Run)
        .where(
            Run.created_at >= since,
            (Run.status == RunStatus.FAILED)
            | ((Run.status == RunStatus.COMPLETED) & (Run.emails_failed > 0)),
        )
        .order_by(Run.created_at.desc())
        .limit(10)
    )

    # The latest listing error per inbox, if that inbox's most recent finished run reported one.
    inboxes_with_errors: list[AttentionInbox] = []
    for inbox in await session.scalars(select(Inbox).order_by(Inbox.name)):
        latest = (
            await session.execute(
                select(RunInbox.error, Run.id)
                .join(Run, Run.id == RunInbox.run_id)
                .where(RunInbox.inbox_id == inbox.id, Run.finished_at.is_not(None))
                .order_by(Run.finished_at.desc())
                .limit(1)
            )
        ).first()
        if latest and latest[0]:
            inboxes_with_errors.append(
                AttentionInbox(
                    inbox_id=inbox.id,
                    name=inbox.name,
                    email_address=inbox.email_address,
                    error=latest[0],
                    run_id=latest[1],
                )
            )

    return DashboardAttention(
        labels_without_condition=without,
        labels_stale=stale,
        labels_never_run=never,
        labels_near_threshold=near,
        labels_likely_misses=misses,
        near_window=NEAR_WINDOW,
        runs_with_problems=[
            AttentionRun(
                run_id=run.id,
                name=run.name,
                status=run.status.value,
                emails_failed=run.emails_failed,
                error=run.error,
                created_at=run.created_at,
            )
            for run in problem_runs
        ],
        inboxes_with_errors=inboxes_with_errors,
    )


async def status(session: AsyncSession) -> DashboardStatus:
    settings = get_settings()
    window = settings.gmail_quota_window_seconds
    limit = max(
        1, int(settings.gmail_quota_units_per_minute * settings.gmail_quota_utilisation * window / 60)
    )
    current_window = int(datetime.now(UTC).timestamp() // window)

    result: list[InboxStatus] = []
    for inbox in await session.scalars(select(Inbox).order_by(Inbox.name)):
        covered = and_(
            RunInbox.inbox_id == inbox.id, RunInbox.error.is_(None), Run.status == RunStatus.COMPLETED
        )
        last_scanned, scanned_since = (
            await session.execute(
                select(func.max(Run.finished_at), func.min(Run.window_start))
                .select_from(RunInbox)
                .join(Run, Run.id == RunInbox.run_id)
                .where(covered)
            )
        ).one()
        try:
            used = int(await redis_client.get(f"quota:gmail:{inbox.id}:{current_window}") or 0)
        except Exception:  # Redis down: the dashboard still renders
            used = 0
        result.append(
            InboxStatus(
                inbox_id=inbox.id,
                name=inbox.name,
                email_address=inbox.email_address,
                last_scanned_at=last_scanned,
                scanned_since=scanned_since,
                quota_used=used,
                quota_limit=limit,
                quota_window_seconds=window,
            )
        )
    return DashboardStatus(inboxes=result)


async def coverage(session: AsyncSession) -> DashboardCoverage:
    """For each label (current condition): date ranges completed runs have covered in every connected
    inbox, merged. Gaps are what a run would still need to classify."""
    inbox_ids = list(await session.scalars(select(Inbox.id)))
    rows: list[LabelCoverageRow] = []
    earliest: datetime | None = None
    for label in await session.scalars(
        select(Label).where(Label.filter_condition.is_not(None)).order_by(Label.name)
    ):
        runs = await session.execute(
            select(Run.window_start, Run.window_end, RunInbox.inbox_id)
            .join(RunLabel, RunLabel.run_id == Run.id)
            .join(RunInbox, RunInbox.run_id == Run.id)
            .where(
                Run.status == RunStatus.COMPLETED,
                RunLabel.label_id == label.id,
                RunLabel.filter_condition == label.filter_condition,
                RunInbox.error.is_(None),
            )
        )
        per_inbox: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
        for start, end, inbox_id in runs:
            per_inbox.setdefault(inbox_id, []).append((start, end))
        covered = intersect_all([merge_ranges(per_inbox.get(i, [])) for i in inbox_ids]) if inbox_ids else []
        if covered and (earliest is None or covered[0][0] < earliest):
            earliest = covered[0][0]
        rows.append(
            LabelCoverageRow(
                label_id=label.id,
                name=label.name,
                color=label.color,
                covered=[CoveredSpan(start=s, end=e) for s, e in covered],
            )
        )
    return DashboardCoverage(span_start=earliest, span_end=datetime.now(UTC), labels=rows)


async def recent(session: AsyncSession, limit: int = 10) -> DashboardRecent:
    rows = await session.execute(
        select(Email, Inbox.name, Label, EmailLabel.probability, EmailLabel.updated_at)
        .join(EmailLabel, EmailLabel.email_id == Email.id)
        .join(Label, Label.id == EmailLabel.label_id)
        .join(Inbox, Inbox.id == Email.inbox_id)
        .order_by(Email.sent_at.desc())
        .limit(limit)
    )
    return DashboardRecent(
        matches=[
            RecentMatch(
                email_id=email.id,
                sent_at=email.sent_at,
                from_address=email.from_address,
                subject=email.subject,
                inbox_name=inbox_name,
                label_id=label.id,
                label_name=label.name,
                color=label.color,
                probability=probability,
                labelled_at=labelled_at,
            )
            for email, inbox_name, label, probability, labelled_at in rows
        ]
    )
