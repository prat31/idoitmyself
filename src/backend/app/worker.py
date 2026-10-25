"""Celery app and scan tasks.
Worker: celery -A app.worker worker -Q scans --loglevel=INFO
Beat:   celery -A app.worker beat --loglevel=INFO   (fires scans.tick at :00/:30 with a 30-minute interval)

Three kinds of task on the `scans` queue:
- scans.tick: queue a scheduled scan for every inbox an active filter covers (fixed time windows).
- scans.discover(scan_id): list the scan's new emails, then publish them as scans.process batches.
- scans.process(scan_id, message_ids, attempt): fetch, filter and label one batch.
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
    beat_schedule={
        "scan-inboxes": {
            "task": TICK_TASK,
            # Fixed clock boundaries (UTC), e.g. :00 and :30, not "every 30 minutes since beat started".
            "schedule": crontab(minute=f"*/{get_settings().scan_interval_minutes}"),
        }
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
