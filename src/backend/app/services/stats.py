"""Read-only statistics over stored emails and their IDIM labels. Provider-agnostic: everything is
computed from `emails` / `email_labels`, keyed on each email's sent time."""

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.email import Email, EmailLabel
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.run import Run
from app.schemas.stats import (
    EmailLabelRef,
    EmailPage,
    Granularity,
    InboxCount,
    LabelCount,
    LabelledEmail,
    LabelStats,
    Overview,
    SenderCount,
    StatsTotals,
    TimelineBucket,
)

TOP_SENDERS = 10
MAX_BUCKETS = 400


class StatsQueryError(ValueError):
    """Invalid stats parameters (e.g. unknown timezone). Message is user-facing."""


def parse_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError) as exc:
        raise StatsQueryError(f"Unknown timezone: {name}") from exc


def choose_granularity(span: timedelta) -> Granularity:
    if span <= timedelta(days=45):
        return "day"
    if span <= timedelta(days=200):
        return "week"
    return "month"


def bucket_start(day: date, granularity: Granularity) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())  # ISO weeks start Monday, like date_trunc('week')
    if granularity == "month":
        return day.replace(day=1)
    return day


def next_bucket(start: date, granularity: Granularity) -> date:
    if granularity == "day":
        return start + timedelta(days=1)
    if granularity == "week":
        return start + timedelta(days=7)
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def fill_buckets(
    counts: dict[date, tuple[int, int]], first: date, last: date, granularity: Granularity
) -> list[TimelineBucket]:
    """Every bucket from first..last (inclusive), zero-filled, so charts have a continuous axis."""
    buckets: list[TimelineBucket] = []
    cursor = bucket_start(first, granularity)
    end = bucket_start(last, granularity)
    while cursor <= end and len(buckets) < MAX_BUCKETS:
        emails, labelled = counts.get(cursor, (0, 0))
        buckets.append(TimelineBucket(start=cursor, emails=emails, labelled=labelled))
        cursor = next_bucket(cursor, granularity)
    return buckets


def _local_day(column, tz: ZoneInfo):
    return func.date(func.timezone(tz.key, column))


def _email_filters(
    start: datetime | None,
    end: datetime | None,
    inbox_id: uuid.UUID | None,
    label_ids: list[uuid.UUID],
) -> list:
    conditions = []
    if start is not None:
        conditions.append(Email.sent_at >= start)
    if end is not None:
        conditions.append(Email.sent_at < end)
    if inbox_id is not None:
        conditions.append(Email.inbox_id == inbox_id)
    if label_ids:
        # Aliased so it never auto-correlates with an outer query that also selects email_labels.
        filter_link = aliased(EmailLabel)
        conditions.append(
            exists().where(filter_link.email_id == Email.id, filter_link.label_id.in_(label_ids))
        )
    return conditions


async def _timeline(
    session: AsyncSession,
    filters: list,
    labelled_condition,
    tz: ZoneInfo,
    first: date | None,
    last: date | None,
) -> tuple[Granularity, list[TimelineBucket]]:
    if first is None or last is None:
        bounds = (
            await session.execute(select(func.min(Email.sent_at), func.max(Email.sent_at)).where(*filters))
        ).one()
        if bounds[0] is None:
            today = datetime.now(tz).date()
            return "day", fill_buckets({}, today, today, "day")
        first = first or bounds[0].astimezone(tz).date()
        last = last or bounds[1].astimezone(tz).date()
    granularity = choose_granularity(timedelta(days=(last - first).days + 1))
    bucket = func.date(func.date_trunc(granularity, func.timezone(tz.key, Email.sent_at)))
    rows = await session.execute(
        select(bucket, func.count(), func.count().filter(labelled_condition)).where(*filters).group_by(bucket)
    )
    counts = {row[0]: (row[1], row[2]) for row in rows}
    return granularity, fill_buckets(counts, first, last, granularity)


async def _by_inbox(session: AsyncSession, filters: list) -> list[InboxCount]:
    rows = await session.execute(
        select(Inbox.id, Inbox.name, Inbox.email_address, func.count(Email.id))
        .join(Email, Email.inbox_id == Inbox.id)
        .where(*filters)
        .group_by(Inbox.id)
        .order_by(func.count(Email.id).desc())
    )
    return [InboxCount(inbox_id=r[0], name=r[1], email_address=r[2], emails=r[3]) for r in rows]


async def _top_senders(session: AsyncSession, filters: list) -> list[SenderCount]:
    sender = func.coalesce(Email.from_address, literal("(unknown)"))
    rows = await session.execute(
        select(sender, func.count())
        .where(*filters)
        .group_by(sender)
        .order_by(func.count().desc(), sender)
        .limit(TOP_SENDERS)
    )
    return [SenderCount(sender=r[0], emails=r[1]) for r in rows]


async def overview(
    session: AsyncSession,
    *,
    start: datetime | None,
    end: datetime | None,
    inbox_id: uuid.UUID | None,
    label_ids: list[uuid.UUID],
    tz_name: str,
) -> Overview:
    tz = parse_timezone(tz_name)
    filters = _email_filters(start, end, inbox_id, label_ids)
    label_scope = [EmailLabel.label_id.in_(label_ids)] if label_ids else []
    has_label = exists().where(EmailLabel.email_id == Email.id, *label_scope)

    emails, labelled, senders = (
        await session.execute(
            select(
                func.count(), func.count().filter(has_label), func.count(func.distinct(Email.from_address))
            ).where(*filters)
        )
    ).one()
    assignments = await session.scalar(
        select(func.count())
        .select_from(EmailLabel)
        .join(Email, Email.id == EmailLabel.email_id)
        .where(*filters, *label_scope)
    )

    # Every label (or just the filtered ones), including those with no emails in range.
    counts = dict(
        (
            await session.execute(
                select(EmailLabel.label_id, func.count())
                .join(Email, Email.id == EmailLabel.email_id)
                .where(*filters, *label_scope)
                .group_by(EmailLabel.label_id)
            )
        ).all()
    )
    label_query = select(Label).order_by(Label.name)
    if label_ids:
        label_query = label_query.where(Label.id.in_(label_ids))
    by_label = sorted(
        (
            LabelCount(label_id=label.id, name=label.name, color=label.color, emails=counts.get(label.id, 0))
            for label in await session.scalars(label_query)
        ),
        key=lambda item: (-item.emails, item.name),
    )

    first = start.astimezone(tz).date() if start else None
    last = (end - timedelta(microseconds=1)).astimezone(tz).date() if end else None
    granularity, timeline = await _timeline(session, filters, has_label, tz, first, last)

    return Overview(
        window_start=start,
        window_end=end,
        granularity=granularity,
        totals=StatsTotals(
            emails=emails, labelled_emails=labelled, label_assignments=assignments or 0, senders=senders
        ),
        timeline=timeline,
        by_label=by_label,
        by_inbox=await _by_inbox(session, filters),
        top_senders=await _top_senders(session, filters),
    )


async def label_stats(session: AsyncSession, label: Label, tz_name: str) -> LabelStats:
    tz = parse_timezone(tz_name)
    filters = _email_filters(None, None, None, [label.id])
    link = and_(EmailLabel.email_id == Email.id, EmailLabel.label_id == label.id)
    emails, avg_probability, first_sent, last_sent = (
        await session.execute(
            select(
                func.count(),
                func.avg(EmailLabel.probability),
                func.min(Email.sent_at),
                func.max(Email.sent_at),
            )
            .select_from(Email)
            .join(EmailLabel, link)
        )
    ).one()
    recent = await session.scalar(
        select(func.count())
        .select_from(Email)
        .join(EmailLabel, link)
        .where(Email.sent_at >= datetime.now(UTC) - timedelta(days=30))
    )
    granularity, timeline = await _timeline(session, filters, literal(True), tz, None, None)
    return LabelStats(
        label_id=label.id,
        granularity=granularity,
        emails=emails,
        emails_last_30_days=recent or 0,
        avg_probability=float(avg_probability) if avg_probability is not None else None,
        first_sent_at=first_sent,
        last_sent_at=last_sent,
        timeline=timeline,
        by_inbox=await _by_inbox(session, filters),
        top_senders=await _top_senders(session, filters),
    )


async def label_emails(session: AsyncSession, label: Label, page: int, page_size: int) -> EmailPage:
    """Emails carrying `label`, newest first."""
    total = await session.scalar(
        select(func.count()).select_from(EmailLabel).where(EmailLabel.label_id == label.id)
    )
    query: Select = (
        select(Email, EmailLabel.probability, EmailLabel.run_id, Run.name, Inbox.name)
        .join(EmailLabel, and_(EmailLabel.email_id == Email.id, EmailLabel.label_id == label.id))
        .join(Inbox, Inbox.id == Email.inbox_id)
        .outerjoin(Run, Run.id == EmailLabel.run_id)
        .order_by(Email.sent_at.desc(), Email.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(query)).all()
    email_ids = [row[0].id for row in rows]

    others: dict[uuid.UUID, list[EmailLabelRef]] = {email_id: [] for email_id in email_ids}
    if email_ids:
        other_rows = await session.execute(
            select(EmailLabel.email_id, Label.id, Label.name, Label.color)
            .join(Label, Label.id == EmailLabel.label_id)
            .where(EmailLabel.email_id.in_(email_ids), EmailLabel.label_id != label.id)
            .order_by(Label.name)
        )
        for email_id, label_id, name, color in other_rows:
            others[email_id].append(EmailLabelRef(label_id=label_id, name=name, color=color))

    return EmailPage(
        items=[
            LabelledEmail(
                id=email.id,
                inbox_id=email.inbox_id,
                inbox_name=inbox_name,
                sent_at=email.sent_at,
                from_address=email.from_address,
                subject=email.subject,
                snippet=email.snippet,
                probability=probability,
                run_id=run_id,
                run_name=run_name,
                other_labels=others[email.id],
            )
            for email, probability, run_id, run_name, inbox_name in rows
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )
