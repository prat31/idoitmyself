"""Celery app, scan tasks and processor tasks.
Scan worker:      celery -A app.worker worker -Q scans --loglevel=INFO
Processor worker: celery -A app.worker worker -Q processors --loglevel=INFO
Beat:             celery -A app.worker beat --loglevel=INFO   (scans.tick every 15 minutes)

Three kinds of task on the `scans` queue:
- scans.tick: queue a scheduled scan for every inbox an active filter covers (fixed time windows).
- scans.discover(scan_id): list the scan's new emails, then publish them as scans.process batches.
- scans.process(scan_id, message_ids, attempt): fetch, filter and label one batch, then publish the
  processor runs queued for the labels it added.
And on the `processors` queue:
- processors.run(run_id): run one processor on one email, then publish the actions it made due now.
- processors.sweep (beat, every 5 minutes): re-publish runs whose message was lost.
- processors.deliver_action(action_id, attempt): deliver one action (e.g. a notification), once.
- processors.actions_tick (beat, every minute): publish the actions whose time has come.
Transient failures (rate limits, 5xx, network) are never waited on in the worker: the work is
published back to the broker with a `countdown` (exponential back-off with jitter, honouring
Retry-After), and the pool process moves on.
"""

import asyncio
import logging
import random
import uuid
from collections.abc import Awaitable, Callable

import httpx
from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.quota import QuotaExhausted
from app.core.redis import close_loop_redis
from app.core.retry import TransientError, backoff_seconds

logger = logging.getLogger(__name__)

SCAN_QUEUE = "scans"
TICK_TASK = "scans.tick"
DISCOVER_TASK = "scans.discover"
PROCESS_BATCH_TASK = "scans.process"
PROCESSOR_QUEUE = "processors"
PROCESSOR_RUN_TASK = "processors.run"
PROCESSOR_SWEEP_TASK = "processors.sweep"
DELIVER_ACTION_TASK = "processors.deliver_action"
ACTIONS_TICK_TASK = "processors.actions_tick"
SETTLE_SECONDS = 60

celery_app = Celery("idim", broker=get_settings().celery_broker_url)
celery_app.conf.update(
    task_default_queue=SCAN_QUEUE,
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # RabbitMQ 4 rejects the transient non-exclusive queues Celery uses for remote control (pidbox);
    # we don't use remote control, gossip or mingle. Our task queue itself is durable.
    worker_enable_remote_control=False,
    task_routes={"processors.*": {"queue": PROCESSOR_QUEUE}},
    beat_schedule={
        "scan-inboxes": {
            "task": TICK_TASK,
            # Every quarter hour on the clock, so each boundary of the stored interval (from midnight in
            # SCAN_TIMEZONE, which may be offset by :30 or :45 from UTC) gets a tick right on time. Ticks
            # between boundaries do nothing (see start_due_scans).
            "schedule": crontab(minute="*/15"),
        },
        "sweep-processor-runs": {"task": PROCESSOR_SWEEP_TASK, "schedule": crontab(minute="*/5")},
        "deliver-due-actions": {"task": ACTIONS_TICK_TASK, "schedule": crontab(minute="*")},
    },
)


def _run_async[T](work: Callable[[Callable[[], AsyncSession], httpx.AsyncClient], Awaitable[T]]) -> T:
    """Run async work in a fresh event loop with its own (unpooled) engine and HTTP client."""

    async def main() -> T:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                return await work(async_sessionmaker(engine, expire_on_commit=False), client)
        finally:
            await close_loop_redis()
            await engine.dispose()

    return asyncio.run(main())


def _pacing_delay(retry_after: float | None) -> float:
    """Next budget window, plus a random spread so paced work trickles back instead of stampeding."""
    return (retry_after or 0) + random.uniform(0, get_settings().scan_pacing_spread_seconds)


def _delay(attempt: int, retry_after: float | None = None) -> float:
    settings = get_settings()
    return backoff_seconds(
        attempt,
        base=settings.scan_retry_base_seconds,
        cap=settings.scan_retry_max_seconds,
        retry_after=retry_after,
    )


@celery_app.task(name=TICK_TASK)
def tick_task() -> None:
    from app.services.scan_engine import start_due_scans

    for scan_id in _run_async(lambda sf, _client: start_due_scans(sf)):
        # A short wait past the boundary, so mail received just before it is in the provider's index.
        discover_task.apply_async(args=[str(scan_id)], countdown=SETTLE_SECONDS)


@celery_app.task(name=DISCOVER_TASK, bind=True)
def discover_task(self, scan_id: str, provider_errors: int = 0) -> None:
    from app.services.scan_engine import discover, fail_scan

    settings = get_settings()
    sid = uuid.UUID(scan_id)
    try:
        ids = _run_async(lambda sf, client: discover(sid, session_factory=sf, client=client))
    except QuotaExhausted as exc:
        # Our own budget is spent for this window: try again next window, without using an attempt.
        raise self.retry(
            countdown=_pacing_delay(exc.retry_after),
            max_retries=None,
            kwargs={"provider_errors": provider_errors},
        ) from exc
    except TransientError as exc:
        attempt = provider_errors
        if attempt + 1 >= settings.scan_max_attempts:
            message = f"Couldn't list emails after {attempt + 1} attempts: {exc}"
            _run_async(lambda sf, _client: fail_scan(sf, sid, message))
            return
        countdown = _delay(attempt, exc.retry_after)
        logger.warning(
            "Scan %s: listing deferred %.0fs (attempt %s): %s", scan_id, countdown, attempt + 1, exc
        )
        # Re-publish this task to the broker with a delay; the worker process is freed immediately.
        raise self.retry(
            countdown=countdown, max_retries=None, kwargs={"provider_errors": attempt + 1}
        ) from exc

    size = settings.scan_batch_size
    for start in range(0, len(ids), size):
        process_batch_task.apply_async(args=[scan_id, ids[start : start + size], 0])
    logger.info("Scan %s: %s emails in %s batches", scan_id, len(ids), -(-len(ids) // size))


@celery_app.task(name=PROCESS_BATCH_TASK)
def process_batch_task(scan_id: str, message_ids: list[str], attempt: int = 0) -> None:
    from app.services.scan_engine import process_batch

    settings = get_settings()
    sid = uuid.UUID(scan_id)
    outcome = _run_async(
        lambda sf, client: process_batch(
            sid,
            message_ids,
            attempt=attempt,
            max_attempts=settings.scan_max_attempts,
            session_factory=sf,
            client=client,
        )
    )
    publish_processor_runs(outcome.processor_runs)
    if outcome.paced:
        process_batch_task.apply_async(
            args=[scan_id, outcome.paced, attempt], countdown=_pacing_delay(outcome.paced_after)
        )
    if outcome.deferred:
        countdown = _delay(attempt, outcome.retry_after)
        logger.info(
            "Scan %s: re-queuing %s emails in %.0fs (attempt %s)",
            scan_id,
            len(outcome.deferred),
            countdown,
            attempt + 2,
        )
        process_batch_task.apply_async(args=[scan_id, outcome.deferred, attempt + 1], countdown=countdown)


def publish_processor_runs(run_ids: list[uuid.UUID]) -> None:
    for run_id in run_ids:
        celery_app.send_task(PROCESSOR_RUN_TASK, args=[str(run_id)])


def publish_actions(action_ids: list[uuid.UUID]) -> None:
    for action_id in action_ids:
        celery_app.send_task(DELIVER_ACTION_TASK, args=[str(action_id)])


# Processor runs and actions are idempotent, so their messages are acked only once handled: a worker
# killed mid-task leaves them to be delivered again (at least once).
@celery_app.task(name=PROCESSOR_RUN_TASK, acks_late=True, reject_on_worker_lost=True)
def processor_run_task(run_id: str) -> None:
    from app.services.processor_engine import run_processor

    settings = get_settings()
    outcome = _run_async(
        lambda sf, client: run_processor(
            uuid.UUID(run_id), max_attempts=settings.scan_max_attempts, session_factory=sf, client=client
        )
    )
    publish_actions(outcome.due_actions)
    if outcome.retry is None:
        return
    retry = outcome.retry
    countdown = _pacing_delay(retry.retry_after) if retry.paced else _delay(retry.attempt, retry.retry_after)
    processor_run_task.apply_async(args=[run_id], countdown=countdown)


@celery_app.task(name=PROCESSOR_SWEEP_TASK)
def processor_sweep_task() -> None:
    from app.services.processor_engine import stale_runs

    publish_processor_runs(_run_async(lambda sf, _client: stale_runs(sf)))


@celery_app.task(name=DELIVER_ACTION_TASK, acks_late=True, reject_on_worker_lost=True)
def deliver_action_task(action_id: str, attempt: int = 0) -> None:
    from app.services.actions import deliver

    settings = get_settings()
    try:
        _run_async(
            lambda sf, client: deliver(
                uuid.UUID(action_id),
                final_attempt=attempt + 1 >= settings.scan_max_attempts,
                session_factory=sf,
                client=client,
            )
        )
    except TransientError as exc:
        countdown = _delay(attempt, exc.retry_after)
        logger.warning("Action %s deferred %.0fs (attempt %s): %s", action_id, countdown, attempt + 1, exc)
        deliver_action_task.apply_async(args=[action_id, attempt + 1], countdown=countdown)


@celery_app.task(name=ACTIONS_TICK_TASK)
def actions_tick_task() -> None:
    from app.services.actions import due_actions

    publish_actions(_run_async(lambda sf, _client: due_actions(sf)))
