"""App-wide dashboard: scan summary, attention items, live status and recent matches.
Everything is derived from stored data (scans, filters, email_labels) — no provider calls."""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import redis_client
from app.mail.sources import message_url
from app.models.email import Email, EmailLabel
from app.models.filter import Filter, FilterStatus
from app.models.inbox import Inbox
from app.models.label import Label
from app.models.scan import ACTIVE_SCAN_STATUSES, InboxSync, Scan, ScanStatus
from app.schemas.dashboard import (
    AttentionFilter,
    AttentionInbox,
    AttentionLabel,
    AttentionScan,
    DashboardAttention,
    DashboardRecent,
    DashboardStatus,
    DashboardSummary,
    InboxStatus,
    LabelMonth,
    RecentMatch,
)
from app.services.filters import active_filters
from app.services.scans import to_read
from app.services.stats import parse_timezone

RECENT_PROBLEM_DAYS = 30


async def summary(
    session: AsyncSession, *, start: datetime | None, end: datetime | None, tz_name: str
) -> DashboardSummary:
    tz = parse_timezone(tz_name)
    finished = [Scan.finished_at.is_not(None)]
    if start:
        finished.append(Scan.finished_at >= start)
    if end:
        finished.append(Scan.finished_at < end)

    completed, failed, processed, skipped, labelled = (
        await session.execute(
            select(
                func.count().filter(Scan.status == ScanStatus.COMPLETED),
                func.count().filter(Scan.status == ScanStatus.FAILED),
                func.coalesce(func.sum(Scan.emails_processed), 0),
                func.coalesce(func.sum(Scan.emails_skipped), 0),
                func.coalesce(func.sum(Scan.emails_matched), 0),
            ).where(*finished)
        )
    ).one()
    statuses = dict(
        (await session.execute(select(Filter.status, func.count()).group_by(Filter.status))).all()
    )

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

    return DashboardSummary(
        scans_completed=completed,
        scans_failed=failed,
        emails_scanned=int(processed) - int(skipped),
        emails_labelled=int(labelled),
        active_filters=statuses.get(FilterStatus.ACTIVE, 0),
        inactive_filters=statuses.get(FilterStatus.INACTIVE, 0),
        label_months=[
            LabelMonth(
                label_id=label.id,
                display_name=label.display_name,
                color=label.color,
                this_month=per_label.get(label.id, {}).get(this_month, 0),
                last_month=per_label.get(label.id, {}).get(last_month, 0),
            )
            for label in await session.scalars(select(Label).order_by(Label.display_name))
        ],
    )


async def attention(session: AsyncSession) -> DashboardAttention:
    active = Filter.status == FilterStatus.ACTIVE
    never_matched = await session.execute(
        select(Filter.id, Filter.name, Label.display_name)
        .join(Label, Label.id == Filter.label_id)
        .where(active, ~exists().where(EmailLabel.filter_id == Filter.id))
        .order_by(Filter.name)
    )
    unwritten = await session.scalars(
        select(Label).where(~exists().where(Filter.label_id == Label.id, active)).order_by(Label.display_name)
    )

    since = datetime.now(UTC) - timedelta(days=RECENT_PROBLEM_DAYS)
    problem_scans = await session.execute(
        select(Scan, Inbox.name)
        .join(Inbox, Inbox.id == Scan.inbox_id)
        .where(
            Scan.created_at >= since,
            (Scan.status == ScanStatus.FAILED)
            | ((Scan.status == ScanStatus.COMPLETED) & (Scan.emails_failed > 0)),
        )
        .order_by(Scan.created_at.desc())
        .limit(10)
    )

    active_scoped = await active_filters(session)
    inboxes_with_errors: list[AttentionInbox] = []
    inboxes_without_filters: list[AttentionInbox] = []
    for inbox in await session.scalars(select(Inbox).order_by(Inbox.name)):
        if not any(f.covers(inbox) for f in active_scoped):
            inboxes_without_filters.append(
                AttentionInbox(
                    inbox_id=inbox.id,
                    name=inbox.name,
                    email_address=inbox.email_address,
                    error="",
                    scan_id=None,
                )
            )
        latest = await session.scalar(
            select(Scan)
            .where(Scan.inbox_id == inbox.id, Scan.finished_at.is_not(None))
            .order_by(Scan.finished_at.desc())
            .limit(1)
        )
        if latest is not None and latest.status == ScanStatus.FAILED:
            inboxes_with_errors.append(
                AttentionInbox(
                    inbox_id=inbox.id,
                    name=inbox.name,
                    email_address=inbox.email_address,
                    error=latest.error or "Scan failed",
                    scan_id=latest.id,
                )
            )

    return DashboardAttention(
        inboxes_with_errors=inboxes_with_errors,
        scans_with_problems=[
            AttentionScan(
                scan_id=scan.id,
                inbox_name=inbox_name,
                status=scan.status.value,
                emails_failed=scan.emails_failed,
                error=scan.error,
                created_at=scan.created_at,
            )
            for scan, inbox_name in problem_scans
        ],
        filters_never_matched=[
            AttentionFilter(filter_id=fid, name=name, label_display_name=label)
            for fid, name, label in never_matched
        ],
        labels_without_active_filter=[
            AttentionLabel(label_id=label.id, display_name=label.display_name, color=label.color)
            for label in unwritten
        ],
        inboxes_without_filters=inboxes_without_filters,
    )


async def status(session: AsyncSession) -> DashboardStatus:
    settings = get_settings()
    window = settings.gmail_quota_window_seconds
    limit = max(
        1, int(settings.gmail_quota_units_per_minute * settings.gmail_quota_utilisation * window / 60)
    )
    current_window = int(datetime.now(UTC).timestamp() // window)
    scanned_until = dict((await session.execute(select(InboxSync.inbox_id, InboxSync.scanned_until))).all())

    result: list[InboxStatus] = []
    for inbox in await session.scalars(select(Inbox).order_by(Inbox.name)):
        last_completed = await session.scalar(
            select(func.max(Scan.finished_at)).where(
                Scan.inbox_id == inbox.id, Scan.status == ScanStatus.COMPLETED
            )
        )
        active = await session.scalar(
            select(Scan)
            .where(Scan.inbox_id == inbox.id, Scan.status.in_(ACTIVE_SCAN_STATUSES))
            .order_by(Scan.created_at.desc())
            .limit(1)
        )
        try:
            used = int(
                await redis_client.get(f"quota:{inbox.provider.value}:{inbox.id}:{current_window}") or 0
            )
        except Exception:  # Redis down: the dashboard still renders
            used = 0
        result.append(
            InboxStatus(
                inbox_id=inbox.id,
                name=inbox.name,
                email_address=inbox.email_address,
                provider=inbox.provider.value,
                scanned_until=scanned_until.get(inbox.id),
                last_completed_scan_at=last_completed,
                active_scan=to_read(active, inbox.name, inbox.email_address) if active else None,
                quota_used=used,
                quota_limit=limit,
                quota_window_seconds=window,
            )
        )
    return DashboardStatus(scan_interval_minutes=settings.scan_interval_minutes, inboxes=result)


async def recent(session: AsyncSession, limit: int = 10) -> DashboardRecent:
    rows = await session.execute(
        select(
            Email, Inbox.name, Inbox.provider, Inbox.email_address, Label, Filter.name, EmailLabel.applied_at
        )
        .join(EmailLabel, EmailLabel.email_id == Email.id)
        .join(Label, Label.id == EmailLabel.label_id)
        .join(Inbox, Inbox.id == Email.inbox_id)
        .outerjoin(Filter, Filter.id == EmailLabel.filter_id)
        .order_by(EmailLabel.applied_at.desc(), Email.sent_at.desc())
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
                label_display_name=label.display_name,
                label_color=label.color,
                filter_name=filter_name,
                applied_at=applied_at,
                open_url=message_url(provider, address, email.provider_message_id),
            )
            for email, inbox_name, provider, address, label, filter_name, applied_at in rows
        ]
    )
