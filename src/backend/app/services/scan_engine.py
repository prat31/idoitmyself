"""Scans inboxes and runs new emails through the active filters. Three steps, each a Celery task (see
app/worker.py):

1. `start_due_scans` (the tick): at each fixed boundary of the scan interval (set on the Scans page,
   e.g. every 3 hours from midnight in SCAN_TIMEZONE), queue a scheduled scan for every inbox covered
   by an active filter's scope, over the window from where its last scheduled scan stopped up to the
   boundary. Ad hoc scans are queued by the API instead.
2. `discover` lists the emails received in the scan's window (and, for a scheduled scan, records that
   the inbox is scanned up to the window's end).
3. `process_batch` handles a batch: emails already stored are skipped (filters only see new email);
   the rest are fetched, stored (metadata only), and run through the active filters covering the inbox,
   whose labels are added, and runs are queued for the processors on the labels just added (see
   app.services.processor_engine). Jev is asked only about the AI conditions that could still change a
   filter's result for the email (one call per email). Filters never remove labels. Transient failures
   come back as deferred work, which the task re-publishes to the broker with a delay; workers never
   sleep to retry.

A scan completes when processed + failed reaches the number found. Provider-agnostic: mailbox access
goes through MailSource."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.quota import QuotaExhausted
from app.core.retry import TransientError
from app.filters.evaluate import Answers, CompiledRule, compile_rule
from app.filters.rule import Rule
from app.mail.sources import open_mail_source
from app.mail.types import FetchedEmail, MailSource, MailSourceError
from app.models.email import Email, EmailLabel
from app.models.filter import Filter
from app.models.inbox import Inbox
from app.models.scan import ACTIVE_SCAN_STATUSES, InboxSync, Scan, ScanKind, ScanStatus
from app.services import jev
from app.services.filters import active_filters, active_filters_for, has_ai_conditions
from app.services.processor_engine import create_runs
from app.services.scans import scan_interval, schedule_boundary

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]
OpenSourceFn = Callable[[Inbox, httpx.AsyncClient, SessionFactory], MailSource]


@dataclass(frozen=True)
class CompiledFilter:
    filter_id: uuid.UUID
    label_id: uuid.UUID
    matches: CompiledRule


@dataclass
class BatchOutcome:
    """What a batch couldn't finish, to be re-queued with a delay:
    - `deferred`: hit a provider error (rate limit, 5xx, network) — retried with back-off, and it
      counts as an attempt;
    - `paced`: held back by our own quota budget, or never started because the batch was throttled —
      re-queued for the next budget window without using an attempt.

    `processor_runs` are the runs queued for labels this batch added, to publish."""

    deferred: list[str] = field(default_factory=list)
    retry_after: float | None = None
    paced: list[str] = field(default_factory=list)
    paced_after: float | None = None
    processor_runs: list[uuid.UUID] = field(default_factory=list)


def matching_labels(
    filters: list[CompiledFilter], email: FetchedEmail, answers: Answers | None = None
) -> dict[uuid.UUID, uuid.UUID]:
    """label_id -> the first filter (in creation order) that matched and adds it. `answers` are Jev's
    for the email's AI questions (see pending_questions)."""
    labels: dict[uuid.UUID, uuid.UUID] = {}
    for f in filters:
        if f.label_id not in labels and f.matches(email, answers):
            labels[f.label_id] = f.filter_id
    return labels


def pending_questions(filters: list[CompiledFilter], email: FetchedEmail) -> dict[str, str]:
    """The AI questions (key -> description) to ask Jev about this email: those that could change
    whether a filter matches. A filter whose label an earlier filter already adds for sure needs
    nothing. Empty for most emails, so Jev is only called when its answer matters."""
    questions: dict[str, str] = {}
    certain: set[uuid.UUID] = set()
    for f in filters:
        if f.label_id in certain:
            continue
        pending = f.matches.pending(email)
        if not pending and f.matches(email):
            certain.add(f.label_id)
        questions |= {key: f.matches.questions[key] for key in pending}
    return questions


def compile_filters(filters: list[Filter]) -> list[CompiledFilter]:
    compiled: list[CompiledFilter] = []
    threshold = get_settings().jev_threshold
    for f in filters:
        try:
            rule = compile_rule(Rule.model_validate(f.rule), threshold)
            compiled.append(CompiledFilter(f.id, f.label_id, rule))
        except ValueError as exc:  # stored rule no longer valid (e.g. a field was removed)
            logger.error("Filter %s (%s) skipped: invalid rule: %s", f.id, f.name, exc)
    return compiled


async def start_due_scans(session_factory: SessionFactory, now: datetime | None = None) -> list[uuid.UUID]:
    """The tick (Celery beat, every 15 minutes): queue a scheduled scan per inbox an active filter covers,
    once a boundary of the stored interval (every interval from midnight in SCAN_TIMEZONE) has passed
    since its last one: for emails received from where its last scheduled scan stopped (or one interval
    back, the first time) up to the boundary. Ticks between boundaries find nothing to do. A changed
    interval applies from the next tick. Windows join up, so nothing is missed or
    read twice; after downtime the next window simply spans the gap.

    An inbox whose scheduled scan is still in flight is skipped this time (its next window catches up).
    Ad hoc scans run alongside. Any scan with no progress for SCAN_STALE_MINUTES is marked failed first,
    so it can't block the inbox forever. Returns the new scans' ids (the caller publishes them)."""
    settings = get_settings()
    now = now or datetime.now(UTC)
    stale_before = now - timedelta(minutes=settings.scan_stale_minutes)
    created: list[uuid.UUID] = []
    async with session_factory() as session:
        interval = await scan_interval(session)
        boundary = schedule_boundary(now, interval)
        active = await active_filters(session)
        scanned_until = dict(
            (await session.execute(select(InboxSync.inbox_id, InboxSync.scanned_until))).all()  # type: ignore[arg-type]
        )
        for inbox in await session.scalars(select(Inbox).order_by(Inbox.created_at)):
            if not any(f.covers(inbox) for f in active):
                continue
            in_flight = list(
                await session.scalars(
                    select(Scan).where(Scan.inbox_id == inbox.id, Scan.status.in_(ACTIVE_SCAN_STATUSES))
                )
            )
            for scan in in_flight:
                if scan.updated_at < stale_before:
                    scan.status = ScanStatus.FAILED
                    scan.error = f"No progress for {settings.scan_stale_minutes} minutes; marked failed"
                    scan.finished_at = now
            if any(s.status != ScanStatus.FAILED and s.kind == ScanKind.SCHEDULED for s in in_flight):
                continue
            start = scanned_until.get(inbox.id) or boundary - timedelta(minutes=interval)
            if start >= boundary:
                continue  # this window was already scanned (the tick runs more often than most intervals)
            scan = Scan(
                inbox_id=inbox.id,
                kind=ScanKind.SCHEDULED,
                status=ScanStatus.QUEUED,
                window_start=start,
                window_end=boundary,
            )
            session.add(scan)
            await session.flush()
            created.append(scan.id)
        await session.commit()
    if created:
        logger.info("Tick %s: queued %s scans", boundary.isoformat(), len(created))
    return created


async def discover(
    scan_id: uuid.UUID,
    *,
    session_factory: SessionFactory,
    client: httpx.AsyncClient,
    open_source: OpenSourceFn = open_mail_source,
) -> list[str]:
    """List the emails received in the scan's window. For a scheduled scan, also record that the inbox
    is scanned up to the window's end (same transaction), so the next one starts there. Returns the
    ids to publish as batches. Raises TransientError if listing should be retried later (nothing is
    recorded in that case, so a retry starts clean). Returns [] for a scan that is missing, already
    discovered, or finished."""
    async with session_factory() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None or scan.status not in ACTIVE_SCAN_STATUSES or scan.discovered_at:
            logger.info("Scan %s: nothing to discover", scan_id)
            return []
        scan.status = ScanStatus.RUNNING
        scan.started_at = scan.started_at or datetime.now(UTC)
        await session.commit()
        inbox = await session.get(Inbox, scan.inbox_id)
        kind, window_start, window_end = scan.kind, scan.window_start, scan.window_end

    if inbox is None:
        await fail_scan(session_factory, scan_id, "Inbox no longer exists")
        return []
    try:
        ids = await open_source(inbox, client, session_factory).list_message_ids(window_start, window_end)  # type: ignore[arg-type]
    except TransientError:
        raise
    except MailSourceError as exc:
        await fail_scan(session_factory, scan_id, str(exc))
        return []

    async with session_factory() as session:
        if kind == ScanKind.SCHEDULED:
            row = insert(InboxSync).values(inbox_id=inbox.id, scanned_until=window_end)
            await session.execute(
                row.on_conflict_do_update(
                    index_elements=[InboxSync.inbox_id],
                    set_={"scanned_until": window_end, "updated_at": func.now()},
                )
            )
        await _mark_discovered(session, scan_id, len(ids))
        await session.commit()
    return await _complete_if_empty(session_factory, scan_id, ids)


async def _mark_discovered(session: AsyncSession, scan_id: uuid.UUID, found: int) -> None:
    await session.execute(
        update(Scan)
        .where(Scan.id == scan_id)
        .values(emails_found=found, discovered_at=func.now(), updated_at=func.now())
    )


async def _complete_if_empty(
    session_factory: SessionFactory, scan_id: uuid.UUID, ids: list[str]
) -> list[str]:
    if not ids:
        await complete_scan_if_done(session_factory, scan_id)
    return ids


async def process_batch(
    scan_id: uuid.UUID,
    message_ids: list[str],
    *,
    attempt: int,
    max_attempts: int,
    session_factory: SessionFactory,
    client: httpx.AsyncClient,
    open_source: OpenSourceFn = open_mail_source,
    ask: jev.AskFn = jev.ask,
    concurrency: int | None = None,
) -> BatchOutcome:
    """Handle a batch of the scan's emails. Never waits on a retry: emails hitting a transient failure
    — and, once throttled, the batch's not-yet-started emails — come back in the outcome to be
    re-published with a delay (see BatchOutcome). After `max_attempts` provider errors an email counts
    as failed; pacing by our own quota budget never uses an attempt."""
    async with session_factory() as session:
        scan = await session.get(Scan, scan_id)
        if scan is None or scan.status != ScanStatus.RUNNING:
            return BatchOutcome()  # scan finished or failed meanwhile
        inbox = await session.get(Inbox, scan.inbox_id)
        if inbox is None:
            await fail_scan(session_factory, scan_id, "Inbox no longer exists")
            return BatchOutcome()
        # The filters active right now whose scope covers this inbox: a filter applies to emails
        # scanned while it's active. Ad hoc scans narrow that to the filters they were asked for.
        candidates = await active_filters_for(session, inbox)
        if scan.kind == ScanKind.ADHOC:
            chosen = {f.id for f in scan.filters}
            candidates = [f for f in candidates if f.id in chosen]
            if not candidates:
                await fail_scan(session_factory, scan_id, "None of its filters is active any more")
                return BatchOutcome()
        # Without OPENROUTER_API_KEY, filters with AI conditions are skipped (the others still run).
        if not jev.is_configured() and (skipped := [f for f in candidates if has_ai_conditions(f)]):
            logger.warning(
                "Scan %s: OPENROUTER_API_KEY isn't set; skipping filters with AI conditions: %s",
                scan_id,
                ", ".join(f.name for f in skipped),
            )
            candidates = [f for f in candidates if f not in skipped]
            if not candidates and scan.kind == ScanKind.ADHOC:
                error = "Its filters have AI conditions, and OPENROUTER_API_KEY isn't set"
                await fail_scan(session_factory, scan_id, error)
                return BatchOutcome()
        filters = compile_filters(candidates)
        stored = set(
            await session.scalars(
                select(Email.provider_message_id).where(
                    Email.inbox_id == inbox.id, Email.provider_message_id.in_(message_ids)
                )
            )
        )
    if stored:
        await _bump(session_factory, scan_id, processed=len(stored), skipped=len(stored))

    final_attempt = attempt + 1 >= max_attempts
    outcome = BatchOutcome()
    throttled = asyncio.Event()  # back off as a batch: stop starting new work once throttled
    source = open_source(inbox, client, session_factory)
    semaphore = asyncio.Semaphore(concurrency or get_settings().scan_concurrency)

    def defer(message_id: str, retry_after: float | None) -> None:
        outcome.deferred.append(message_id)
        if retry_after is not None:
            outcome.retry_after = max(outcome.retry_after or 0, retry_after)

    def pace(message_id: str, retry_after: float | None) -> None:
        outcome.paced.append(message_id)
        if retry_after is not None:
            outcome.paced_after = max(outcome.paced_after or 0, retry_after)

    async def process(message_id: str) -> None:
        async with semaphore:
            if throttled.is_set():
                pace(message_id, None)  # never tried: don't spend an attempt on it
                return
            try:
                email = await source.fetch(message_id)
                questions = pending_questions(filters, email)
                answers = await ask(client, email, questions) if questions else {}
                labels = matching_labels(filters, email, answers)
                async with session_factory() as session:
                    outcome.processor_runs += await _store(session, scan_id, inbox.id, email, labels)
            except QuotaExhausted as exc:
                throttled.set()
                pace(message_id, exc.retry_after)
            except TransientError as exc:
                if final_attempt:
                    logger.warning(
                        "Scan %s: message %s gave up after %s attempts: %s",
                        scan_id,
                        message_id,
                        max_attempts,
                        exc,
                    )
                    await _bump(session_factory, scan_id, failed=1)
                else:
                    # Logged per email that actually hit the error (not the ones deferred with it), so
                    # the provider's reason — e.g. "403 (rateLimitExceeded)" — is visible in the logs.
                    logger.warning(
                        "Scan %s: message %s deferred (attempt %s/%s): %s",
                        scan_id,
                        message_id,
                        attempt + 1,
                        max_attempts,
                        exc,
                    )
                    throttled.set()
                    defer(message_id, exc.retry_after)
            except jev.JevError as exc:
                if exc.fatal:  # e.g. a bad key or no credits: every email would fail the same way
                    await fail_scan(session_factory, scan_id, str(exc))
                else:
                    logger.warning("Scan %s: message %s failed: %s", scan_id, message_id, exc)
                    await _bump(session_factory, scan_id, failed=1)
            except Exception as exc:  # anything else fails this email, never the batch
                logger.warning("Scan %s: message %s failed: %r", scan_id, message_id, exc)
                await _bump(session_factory, scan_id, failed=1)

    await asyncio.gather(*(process(message_id) for message_id in message_ids if message_id not in stored))

    if outcome.deferred:  # only real provider errors count as retries
        await _bump(session_factory, scan_id, retries=len(outcome.deferred))
    await complete_scan_if_done(session_factory, scan_id)
    return outcome


async def complete_scan_if_done(session_factory: SessionFactory, scan_id: uuid.UUID) -> None:
    """Atomically mark the scan completed once every discovered email is processed or failed. Safe to
    call from any batch; only the one that finishes the last email flips the status."""
    async with session_factory() as session:
        await session.execute(
            update(Scan)
            .where(
                Scan.id == scan_id,
                Scan.status == ScanStatus.RUNNING,
                Scan.discovered_at.is_not(None),
                Scan.emails_processed + Scan.emails_failed >= Scan.emails_found,
            )
            .values(status=ScanStatus.COMPLETED, finished_at=func.now(), updated_at=func.now())
        )
        await session.commit()


async def fail_scan(session_factory: SessionFactory, scan_id: uuid.UUID, error: str) -> None:
    logger.error("Scan %s failed: %s", scan_id, error)
    async with session_factory() as session:
        await session.execute(
            update(Scan)
            .where(Scan.id == scan_id, Scan.status.in_(ACTIVE_SCAN_STATUSES))
            .values(
                status=ScanStatus.FAILED, error=error[:2000], finished_at=func.now(), updated_at=func.now()
            )
        )
        await session.commit()


async def _bump(
    session_factory: SessionFactory,
    scan_id: uuid.UUID,
    *,
    processed: int = 0,
    skipped: int = 0,
    failed: int = 0,
    retries: int = 0,
) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Scan)
            .where(Scan.id == scan_id)
            .values(
                emails_processed=Scan.emails_processed + processed,
                emails_skipped=Scan.emails_skipped + skipped,
                emails_failed=Scan.emails_failed + failed,
                retries=Scan.retries + retries,
                updated_at=func.now(),
            )
        )
        await session.commit()


async def _store(
    session: AsyncSession,
    scan_id: uuid.UUID,
    inbox_id: uuid.UUID,
    email: FetchedEmail,
    labels: dict[uuid.UUID, uuid.UUID],
) -> list[uuid.UUID]:
    """Store the email's metadata, add the matched labels, queue runs of the processors on them and
    bump the scan's counters — one transaction. An email another scan stored meanwhile counts as
    skipped. Returns the queued runs, to publish."""
    row = (
        insert(Email)
        .values(
            id=uuid.uuid4(),
            inbox_id=inbox_id,
            provider_message_id=email.provider_message_id,
            provider_thread_id=email.provider_thread_id,
            internet_message_id=email.internet_message_id,
            sent_at=email.sent_at,
            from_address=email.from_address,
            to_addresses=email.to_addresses,
            cc_addresses=email.cc_addresses,
            subject=email.subject,
            snippet=email.snippet,
            scan_id=scan_id,
        )
        .on_conflict_do_nothing(index_elements=[Email.inbox_id, Email.provider_message_id])
        .returning(Email.id)
    )
    email_id = (await session.execute(row)).scalar_one_or_none()
    added: list[uuid.UUID] = []
    runs: list[uuid.UUID] = []
    if email_id is not None and labels:
        added = list(
            await session.scalars(
                insert(EmailLabel)
                .values(
                    [
                        {
                            "email_id": email_id,
                            "label_id": label_id,
                            "filter_id": filter_id,
                            "scan_id": scan_id,
                        }
                        for label_id, filter_id in labels.items()
                    ]
                )
                .on_conflict_do_nothing()
                .returning(EmailLabel.label_id)
            )
        )
        runs = await create_runs(session, email_id, added)
    applied = len(added)
    await session.execute(
        update(Scan)
        .where(Scan.id == scan_id)
        .values(
            emails_processed=Scan.emails_processed + 1,
            emails_skipped=Scan.emails_skipped + (1 if email_id is None else 0),
            emails_matched=Scan.emails_matched + (1 if applied else 0),
            labels_applied=Scan.labels_applied + applied,
            updated_at=func.now(),
        )
    )
    await session.commit()
    return runs
