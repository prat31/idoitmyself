import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.filter import Filter, FilterStatus
from app.models.inbox import Inbox
from app.models.scan import (
    ACTIVE_SCAN_STATUSES,
    DEFAULT_SCAN_INTERVAL,
    InboxSync,
    Scan,
    ScanKind,
    ScanSettings,
    ScanStatus,
)
from app.schemas.scan import AdhocScanCreate, ScanFilterRef, ScanPage, ScanRead


class AdhocScanError(ValueError):
    """An ad hoc scan request that can't be run. Message is user-facing."""


class ScanNotActiveError(Exception):
    """The scan already finished (completed, failed or cancelled)."""


def to_read(scan: Scan, inbox_name: str, email_address: str) -> ScanRead:
    return ScanRead(
        id=scan.id,
        inbox_id=scan.inbox_id,
        inbox_name=inbox_name,
        inbox_email_address=email_address,
        kind=scan.kind,
        status=scan.status,
        window_start=scan.window_start,
        window_end=scan.window_end,
        started_at=scan.started_at,
        discovered_at=scan.discovered_at,
        finished_at=scan.finished_at,
        error=scan.error,
        emails_found=scan.emails_found,
        emails_processed=scan.emails_processed,
        emails_skipped=scan.emails_skipped,
        emails_failed=scan.emails_failed,
        emails_matched=scan.emails_matched,
        labels_applied=scan.labels_applied,
        retries=scan.retries,
        filters=[ScanFilterRef(id=f.id, name=f.name) for f in scan.filters],
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


async def list_scans(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    active: bool = False,
    inbox_id: uuid.UUID | None = None,
) -> ScanPage:
    """Scans newest first; `active` keeps only queued/running ones."""
    conditions = []
    if active:
        conditions.append(Scan.status.in_(ACTIVE_SCAN_STATUSES))
    if inbox_id is not None:
        conditions.append(Scan.inbox_id == inbox_id)
    total = await session.scalar(select(func.count()).select_from(Scan).where(*conditions))
    rows = await session.execute(
        select(Scan, Inbox.name, Inbox.email_address)
        .join(Inbox, Inbox.id == Scan.inbox_id)
        .where(*conditions)
        .order_by(Scan.created_at.desc(), Scan.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ScanPage(
        items=[to_read(scan, name, address) for scan, name, address in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def scan_interval(session: AsyncSession) -> int:
    """How often scheduled scans run, in minutes (one of SCAN_INTERVALS)."""
    settings = await session.get(ScanSettings, 1)
    return settings.interval_minutes if settings else DEFAULT_SCAN_INTERVAL


async def set_scan_interval(session: AsyncSession, minutes: int) -> None:
    """Takes effect at the next tick: windows still join up, so nothing is missed or read twice."""
    settings = await session.get(ScanSettings, 1)
    if settings is None:
        session.add(ScanSettings(id=1, interval_minutes=minutes))
    else:
        settings.interval_minutes = minutes
    await session.commit()


def _local_boundary(now: datetime, interval_minutes: int) -> datetime:
    local = now.astimezone(ZoneInfo(get_settings().scan_timezone))
    elapsed = local.hour * 60 + local.minute
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + timedelta(minutes=elapsed - elapsed % interval_minutes)


def schedule_boundary(now: datetime, interval_minutes: int) -> datetime:
    """The latest fixed scan boundary at or before `now`: every `interval_minutes` from midnight in
    SCAN_TIMEZONE (with 180, 00:00, 03:00, ... local time). In UTC."""
    return _local_boundary(now, interval_minutes).astimezone(UTC)


def next_run_at(now: datetime, interval_minutes: int) -> datetime:
    """The next fixed boundary after `now`, when the tick queues scheduled scans."""
    return (_local_boundary(now, interval_minutes) + timedelta(minutes=interval_minutes)).astimezone(UTC)


async def scheduled_from(session: AsyncSession, inbox: Inbox, now: datetime) -> datetime:
    """Where scheduled scans take over for an inbox: emails received from here on are (or will be)
    stored by scheduled scans with every active filter. That's where its last scheduled scan stopped
    (or the current boundary, if it has none yet), or earlier if a scheduled scan is still working."""
    sync = await session.get(InboxSync, inbox.id)
    in_flight = await session.scalar(
        select(func.min(Scan.window_start)).where(
            Scan.inbox_id == inbox.id,
            Scan.kind == ScanKind.SCHEDULED,
            Scan.status.in_(ACTIVE_SCAN_STATUSES),
        )
    )
    starts = [sync.scanned_until if sync else schedule_boundary(now, await scan_interval(session))]
    if in_flight:
        starts.append(in_flight)
    return min(starts)


async def create_adhoc_scans(session: AsyncSession, data: AdhocScanCreate) -> list[ScanRead]:
    """Queue one ad hoc scan per inbox the chosen filters cover, each clipped to end where scheduled scans
    take over for that inbox (so an ad hoc scan never stores an email before every active filter has
    seen it). Inboxes left with nothing to scan get no scan. The caller publishes them."""
    now = datetime.now(UTC)
    if data.window_start >= now:
        raise AdhocScanError("The range must be in the past")
    end = min(data.window_end, now)
    filters = list(await session.scalars(select(Filter).where(Filter.id.in_(data.filter_ids))))
    if len(filters) != len(data.filter_ids):
        raise AdhocScanError("Filter not found")
    if any(f.status != FilterStatus.ACTIVE for f in filters):
        raise AdhocScanError("Only active filters can be used in an ad hoc scan")

    inboxes = [
        i
        for i in await session.scalars(select(Inbox).order_by(Inbox.name))
        if any(f.covers(i) for f in filters)
    ]
    if not inboxes:
        raise AdhocScanError("None of these filters covers a connected inbox")
    scans: list[tuple[Scan, Inbox]] = []
    for inbox in inboxes:
        clipped = min(end, await scheduled_from(session, inbox, now))
        if clipped <= data.window_start:
            continue
        scan = Scan(
            inbox_id=inbox.id,
            kind=ScanKind.ADHOC,
            status=ScanStatus.QUEUED,
            window_start=data.window_start,
            window_end=clipped,
            filters=[f for f in filters if f.covers(inbox)],
        )
        session.add(scan)
        scans.append((scan, inbox))
    if not scans:
        raise AdhocScanError(
            "Scheduled scans already cover this range: they store new email with every active filter. "
            "Choose an earlier range."
        )
    await session.commit()
    for scan, _ in scans:
        await session.refresh(scan)
    return [to_read(scan, inbox.name, inbox.email_address) for scan, inbox in scans]


async def cancel_scan(session: AsyncSession, scan_id: uuid.UUID) -> ScanRead | None:
    """Stop a queued or running scan. Batches still queued see it's no longer running and exit without
    calling the provider; emails already stored and labels already added stay. A cancelled scheduled
    scan hands its window back (if no later window was scanned), so the next scheduled run covers it
    again and picks up what was left (stored emails are skipped)."""
    scan = await session.get(Scan, scan_id)
    if scan is None:
        return None
    if scan.status not in ACTIVE_SCAN_STATUSES:
        raise ScanNotActiveError(scan.status.value)
    scan.status = ScanStatus.CANCELLED
    scan.error = "Stopped by the user"
    scan.finished_at = datetime.now(UTC)
    if scan.kind == ScanKind.SCHEDULED:
        sync = await session.get(InboxSync, scan.inbox_id)
        if sync is not None and sync.scanned_until == scan.window_end and scan.window_start is not None:
            sync.scanned_until = scan.window_start
    await session.commit()
    await session.refresh(scan)  # updated_at is set by the database
    inbox = await session.get(Inbox, scan.inbox_id)
    return to_read(scan, inbox.name, inbox.email_address)  # type: ignore[union-attr]
