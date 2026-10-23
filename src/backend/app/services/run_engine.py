"""Executes a run in two steps, each a Celery task (see app/worker.py):

1. `discover` lists the messages in the run's window for every inbox and records the totals.
2. `process_batch` classifies a batch of emails: fetch, ask Jev about the run's labels, apply/remove
   labels. (email, label) pairs already evaluated for the same filter condition are not asked again;
   an email with nothing left to ask is skipped entirely (no Gmail fetch, no model cost) unless the
   run is a re-classify run. Transient failures are returned as deferred work, which the task
   re-publishes to the broker with an exponential back-off delay; workers never sleep to retry.

The run completes when classified + failed reaches the number found. Provider-agnostic: mailbox
access goes through MailSource."""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.quota import QuotaExhausted
from app.core.retry import TransientError
from app.mail.sources import open_mail_source
from app.mail.types import FetchedEmail, MailSource, MailSourceError
from app.models.email import Email, EmailLabel, LabelEvaluation, condition_hash
from app.models.inbox import Inbox
from app.models.run import Run, RunInbox, RunLabel, RunStatus
from app.services import jev
from app.services.jev import JevAnswer, JevError, LabelQuestion

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]
ClassifyFn = Callable[[httpx.AsyncClient, FetchedEmail, list[LabelQuestion]], Awaitable[JevAnswer]]
OpenSourceFn = Callable[[Inbox, httpx.AsyncClient, SessionFactory], MailSource]


@dataclass(frozen=True)
class RunLabelSpec:
    position: int
    label_id: uuid.UUID
    name: str
    filter_condition: str
    threshold: float
    condition_hash: str


@dataclass(frozen=True)
class LabelDecision:
    spec: RunLabelSpec
    probability: float
    matched: bool


def decide(probabilities: dict[str, float], labels: list[RunLabelSpec]) -> list[LabelDecision]:
    """A label matches when Jev's P(yes) reaches the label's threshold."""
    return [
        LabelDecision(
            spec=label,
            probability=probabilities[label.name],
            matched=probabilities[label.name] >= label.threshold,
        )
        for label in labels
    ]


@dataclass(frozen=True)
class WorkItem:
    """One email to classify: which inbox, and the provider's message id."""

    inbox_id: str
    message_id: str

    def to_message(self) -> list[str]:
        return [self.inbox_id, self.message_id]

    @classmethod
    def from_message(cls, value: list[str]) -> "WorkItem":
        return cls(inbox_id=value[0], message_id=value[1])


@dataclass
class BatchOutcome:
    """What a batch couldn't finish, to be re-queued with a delay:
    - `deferred`: hit a provider error (rate limit, 5xx, network) — retried with back-off, and it
      counts as an attempt;
    - `paced`: held back by our own quota budget, or never started because the batch was throttled —
      re-queued for the next budget window without using an attempt."""

    deferred: list[WorkItem] = field(default_factory=list)
    retry_after: float | None = None
    paced: list[WorkItem] = field(default_factory=list)
    paced_after: float | None = None


def _run_label_specs(run: Run) -> list[RunLabelSpec]:
    return [
        RunLabelSpec(
            rl.position,
            rl.label_id,
            rl.label_name,
            rl.filter_condition,
            rl.match_threshold,
            condition_hash(rl.filter_condition),
        )
        for rl in run.labels
        if rl.label_id is not None  # label deleted after the run was requested
    ]


async def discover(
    run_id: uuid.UUID,
    *,
    session_factory: SessionFactory,
    client: httpx.AsyncClient,
    open_source: OpenSourceFn = open_mail_source,
) -> list[WorkItem]:
    """Step 1 of a run: list the messages in the window for every inbox and record the totals.
    Returns the work to publish as batches. Raises TransientError if listing should be retried later
    (nothing is recorded in that case, so a retry starts clean). Returns [] for a run that is missing,
    already discovered, or finished."""
    async with session_factory() as session:
        run = await session.get(Run, run_id)
        if run is None or run.status not in (RunStatus.QUEUED, RunStatus.RUNNING) or run.discovered_at:
            logger.info("Run %s: nothing to discover", run_id)
            return []
        run.status = RunStatus.RUNNING
        run.started_at = run.started_at or datetime.now(UTC)
        await session.commit()
        window = (run.window_start, run.window_end)
        has_labels = bool(_run_label_specs(run))
        run_inboxes = [(ri.position, ri.inbox_id) for ri in run.inboxes]

    if not has_labels:
        await fail_run(session_factory, run_id, "None of the run's labels exist any more")
        return []

    items: list[WorkItem] = []
    results: list[tuple[int, int, str | None]] = []  # (position, found, error)
    for position, inbox_id in run_inboxes:
        async with session_factory() as session:
            inbox = await session.get(Inbox, inbox_id) if inbox_id else None
        if inbox is None:
            results.append((position, 0, "Inbox no longer exists"))
            continue
        try:
            ids = await open_source(inbox, client, session_factory).list_message_ids(*window)
        except TransientError:
            raise
        except MailSourceError as exc:
            results.append((position, 0, str(exc)))
            continue
        results.append((position, len(ids), None))
        items.extend(WorkItem(str(inbox.id), message_id) for message_id in ids)

    errors = [error for _, _, error in results if error]
    async with session_factory() as session:
        for position, found, error in results:
            await session.execute(
                update(RunInbox)
                .where(RunInbox.run_id == run_id, RunInbox.position == position)
                .values(emails_found=found, error=error)
            )
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                emails_found=len(items),
                discovered_at=func.now(),
                error="; ".join(errors) or None,
                updated_at=func.now(),
            )
        )
        await session.commit()

    if not items:
        if errors and len(errors) == len(run_inboxes):
            await fail_run(session_factory, run_id, "; ".join(errors))
        else:
            await complete_run_if_done(session_factory, run_id)
    return items


async def process_batch(
    run_id: uuid.UUID,
    items: list[WorkItem],
    *,
    attempt: int,
    max_attempts: int,
    session_factory: SessionFactory,
    client: httpx.AsyncClient,
    classify: ClassifyFn = jev.classify,
    open_source: OpenSourceFn = open_mail_source,
    concurrency: int | None = None,
) -> BatchOutcome:
    """Step 2 of a run: classify a batch of emails. Never waits on a retry: emails hitting a transient
    failure — and, once throttled, the batch's not-yet-started emails — come back in the outcome to be
    re-published with a delay (see BatchOutcome). After `max_attempts` provider errors an email counts
    as failed; pacing by our own quota budget never uses an attempt."""
    async with session_factory() as session:
        run = await session.get(Run, run_id)
        if run is None or run.status != RunStatus.RUNNING:
            return BatchOutcome()  # run finished or failed meanwhile (e.g. a fatal Jev error)
        labels = _run_label_specs(run)
        reclassify = run.reclassify
        # Answers already on record for these emails (current condition only), unless re-classifying.
        stored = {} if reclassify else await _stored_evaluations(session, items, labels)
    if not labels:
        await fail_run(session_factory, run_id, "None of the run's labels exist any more")
        return BatchOutcome()

    final_attempt = attempt + 1 >= max_attempts
    outcome = BatchOutcome()
    throttled = asyncio.Event()  # back off as a batch: stop starting new work once throttled
    fatal = asyncio.Event()
    sources: dict[str, MailSource | None] = {}
    semaphore = asyncio.Semaphore(concurrency or get_settings().run_concurrency)

    async def source_for(inbox_id: str) -> MailSource | None:
        if inbox_id not in sources:
            async with session_factory() as session:
                inbox = await session.get(Inbox, uuid.UUID(inbox_id))
            sources[inbox_id] = open_source(inbox, client, session_factory) if inbox else None
        return sources[inbox_id]

    def defer(item: WorkItem, retry_after: float | None) -> None:
        outcome.deferred.append(item)
        if retry_after is not None:
            outcome.retry_after = max(outcome.retry_after or 0, retry_after)

    def pace(item: WorkItem, retry_after: float | None) -> None:
        outcome.paced.append(item)
        if retry_after is not None:
            outcome.paced_after = max(outcome.paced_after or 0, retry_after)

    async def process(item: WorkItem) -> None:
        async with semaphore:
            if fatal.is_set():
                return
            if throttled.is_set():
                pace(item, None)  # never tried: don't spend an attempt on it
                return
            try:
                email_id, previous = stored.get((item.inbox_id, item.message_id), (None, {}))
                needed = [label for label in labels if label.label_id not in previous]
                if not needed and email_id is not None:
                    # Every (email, label) pair already answered for the current conditions: no Gmail
                    # fetch, no model call. Thresholds are re-checked against the stored probabilities.
                    decisions = decide({label.name: previous[label.label_id] for label in labels}, labels)
                    async with session_factory() as session:
                        await _store_skipped(session, run_id, email_id, decisions)
                    return
                source = await source_for(item.inbox_id)
                if source is None:
                    raise MailSourceError("Inbox no longer exists")
                email = await source.fetch(item.message_id)
                answer = await classify(
                    client, email, [LabelQuestion(label.name, label.filter_condition) for label in needed]
                )
                probabilities = {
                    label.name: previous[label.label_id] for label in labels if label.label_id in previous
                }
                probabilities.update(answer.probabilities)
                decisions = decide(probabilities, labels)
                async with session_factory() as session:
                    await _store_result(
                        session,
                        run_id,
                        uuid.UUID(item.inbox_id),
                        email,
                        decisions,
                        answer.cost_usd,
                        evaluated={label.label_id for label in needed},
                    )
            except QuotaExhausted as exc:
                throttled.set()
                pace(item, exc.retry_after)
            except TransientError as exc:
                if final_attempt:
                    logger.warning(
                        "Run %s: message %s gave up after %s attempts: %s",
                        run_id,
                        item.message_id,
                        max_attempts,
                        exc,
                    )
                    await _count_failure(session_factory, run_id)
                else:
                    # Logged per email that actually hit the error (not the ones deferred with it), so
                    # the provider's reason — e.g. "403 (rateLimitExceeded)" — is visible in the logs.
                    logger.warning(
                        "Run %s: message %s deferred (attempt %s/%s): %s",
                        run_id,
                        item.message_id,
                        attempt + 1,
                        max_attempts,
                        exc,
                    )
                    throttled.set()
                    defer(item, exc.retry_after)
            except JevError as exc:
                if exc.fatal:
                    fatal.set()
                    await fail_run(session_factory, run_id, str(exc))
                    return
                logger.warning("Run %s: message %s failed: %s", run_id, item.message_id, exc)
                await _count_failure(session_factory, run_id)
            except Exception as exc:  # anything else fails this email, never the batch
                logger.warning("Run %s: message %s failed: %r", run_id, item.message_id, exc)
                await _count_failure(session_factory, run_id)

    await asyncio.gather(*(process(item) for item in items))

    if fatal.is_set():
        return BatchOutcome()
    if outcome.deferred:  # only real provider errors count as retries
        async with session_factory() as session:
            await session.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(retries=Run.retries + len(outcome.deferred), updated_at=func.now())
            )
            await session.commit()
    await complete_run_if_done(session_factory, run_id)
    return outcome


async def complete_run_if_done(session_factory: SessionFactory, run_id: uuid.UUID) -> None:
    """Atomically mark the run completed once every discovered email is classified or failed. Safe to
    call from any batch; only the one that finishes the last email flips the status."""
    async with session_factory() as session:
        await session.execute(
            update(Run)
            .where(
                Run.id == run_id,
                Run.status == RunStatus.RUNNING,
                Run.discovered_at.is_not(None),
                Run.emails_processed + Run.emails_failed >= Run.emails_found,
            )
            .values(status=RunStatus.COMPLETED, finished_at=func.now(), updated_at=func.now())
        )
        await session.commit()


async def fail_run(session_factory: SessionFactory, run_id: uuid.UUID, error: str) -> None:
    logger.error("Run %s failed: %s", run_id, error)
    async with session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == run_id, Run.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
            .values(
                status=RunStatus.FAILED, error=error[:2000], finished_at=func.now(), updated_at=func.now()
            )
        )
        await session.commit()


async def _count_failure(session_factory: SessionFactory, run_id: uuid.UUID) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(emails_failed=Run.emails_failed + 1, updated_at=func.now())
        )
        await session.commit()


async def _stored_evaluations(
    session: AsyncSession, items: list[WorkItem], labels: list[RunLabelSpec]
) -> dict[tuple[str, str], tuple[uuid.UUID, dict[uuid.UUID, float]]]:
    """For a batch: (inbox_id, message_id) -> (email_id, {label_id: probability}) for every stored
    evaluation that is still current (same filter condition as this run asked)."""
    keys = [(uuid.UUID(item.inbox_id), item.message_id) for item in items]
    rows = await session.execute(
        select(Email.id, Email.inbox_id, Email.provider_message_id).where(
            tuple_(Email.inbox_id, Email.provider_message_id).in_(keys)
        )
    )
    emails = {row.id: (str(row.inbox_id), row.provider_message_id) for row in rows}
    result: dict[tuple[str, str], tuple[uuid.UUID, dict[uuid.UUID, float]]] = {
        key: (email_id, {}) for email_id, key in emails.items()
    }
    if not emails:
        return result
    current = {label.label_id: label.condition_hash for label in labels}
    evaluations = await session.execute(
        select(
            LabelEvaluation.email_id,
            LabelEvaluation.label_id,
            LabelEvaluation.probability,
            LabelEvaluation.condition_hash,
        ).where(LabelEvaluation.email_id.in_(emails), LabelEvaluation.label_id.in_(current))
    )
    for email_id, label_id, probability, fingerprint in evaluations:
        if current[label_id] == fingerprint:
            result[emails[email_id]][1][label_id] = probability
    return result


async def _apply_decisions(
    session: AsyncSession, run_id: uuid.UUID, email_id: uuid.UUID, decisions: list[LabelDecision]
) -> tuple[int, int]:
    """Apply matched labels / remove unmatched ones for one email. Returns (applied, removed)."""
    applied = removed = 0
    for decision in decisions:
        if decision.matched:
            link = insert(EmailLabel).values(
                email_id=email_id,
                label_id=decision.spec.label_id,
                probability=decision.probability,
                run_id=run_id,
            )
            await session.execute(
                link.on_conflict_do_update(
                    index_elements=[EmailLabel.email_id, EmailLabel.label_id],
                    set_={
                        "probability": link.excluded.probability,
                        "run_id": run_id,
                        "updated_at": func.now(),
                    },
                )
            )
            applied += 1
            await session.execute(
                update(RunLabel)
                .where(RunLabel.run_id == run_id, RunLabel.position == decision.spec.position)
                .values(matched=RunLabel.matched + 1)
            )
        else:
            result = await session.execute(
                delete(EmailLabel).where(
                    EmailLabel.email_id == email_id, EmailLabel.label_id == decision.spec.label_id
                )
            )
            removed += result.rowcount or 0
    return applied, removed


async def _bump_counters(
    session: AsyncSession, run_id: uuid.UUID, *, applied: int, removed: int, cost: Decimal, skipped: bool
) -> None:
    await session.execute(
        update(Run)
        .where(Run.id == run_id)
        .values(
            emails_processed=Run.emails_processed + 1,
            emails_skipped=Run.emails_skipped + (1 if skipped else 0),
            emails_matched=Run.emails_matched + (1 if applied else 0),
            labels_applied=Run.labels_applied + applied,
            labels_removed=Run.labels_removed + removed,
            cost_usd=Run.cost_usd + cost,
            updated_at=func.now(),
        )
    )


async def _store_skipped(
    session: AsyncSession, run_id: uuid.UUID, email_id: uuid.UUID, decisions: list[LabelDecision]
) -> None:
    """An email whose labels were all answered before: re-apply thresholds, count it as skipped."""
    applied, removed = await _apply_decisions(session, run_id, email_id, decisions)
    await session.execute(update(Email).where(Email.id == email_id).values(last_run_id=run_id))
    await _bump_counters(session, run_id, applied=applied, removed=removed, cost=Decimal(0), skipped=True)
    await session.commit()


async def _store_result(
    session: AsyncSession,
    run_id: uuid.UUID,
    inbox_id: uuid.UUID,
    email: FetchedEmail,
    decisions: list[LabelDecision],
    cost: Decimal,
    *,
    evaluated: set[uuid.UUID],
) -> None:
    """Upsert the email's metadata, record the model's new answers (`evaluated` labels), apply/remove
    labels and bump the run's counters — one transaction."""
    values = {
        "inbox_id": inbox_id,
        "provider_message_id": email.provider_message_id,
        "provider_thread_id": email.provider_thread_id,
        "internet_message_id": email.internet_message_id,
        "sent_at": email.sent_at,
        "from_address": email.from_address,
        "to_addresses": email.to_addresses,
        "cc_addresses": email.cc_addresses,
        "subject": email.subject,
        "snippet": email.snippet,
        "last_run_id": run_id,
    }
    upsert = insert(Email).values(id=uuid.uuid4(), **values)
    upsert = upsert.on_conflict_do_update(
        index_elements=[Email.inbox_id, Email.provider_message_id],
        set_={
            **{k: upsert.excluded[k] for k in values if k not in ("inbox_id", "provider_message_id")},
            "updated_at": func.now(),
        },
    ).returning(Email.id)
    email_id = (await session.execute(upsert)).scalar_one()

    for decision in decisions:
        if decision.spec.label_id not in evaluated:
            continue
        evaluation = insert(LabelEvaluation).values(
            email_id=email_id,
            label_id=decision.spec.label_id,
            probability=decision.probability,
            condition_hash=decision.spec.condition_hash,
            run_id=run_id,
        )
        await session.execute(
            evaluation.on_conflict_do_update(
                index_elements=[LabelEvaluation.email_id, LabelEvaluation.label_id],
                set_={
                    "probability": evaluation.excluded.probability,
                    "condition_hash": evaluation.excluded.condition_hash,
                    "run_id": run_id,
                    "evaluated_at": func.now(),
                },
            )
        )

    applied, removed = await _apply_decisions(session, run_id, email_id, decisions)
    await _bump_counters(session, run_id, applied=applied, removed=removed, cost=cost, skipped=False)
    await session.commit()
