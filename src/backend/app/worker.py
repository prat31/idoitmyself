"""Celery app and run tasks. Start a worker with: celery -A app.worker worker -Q runs --loglevel=INFO

A run is two kinds of task on the `runs` queue:
- runs.execute(run_id): list the run's emails, then publish them as runs.process batches.
- runs.process(run_id, items, attempt): classify one batch.
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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.quota import QuotaExhausted
from app.core.redis import close_loop_redis
from app.core.retry import TransientError, backoff_seconds

logger = logging.getLogger(__name__)

RUN_QUEUE = "runs"
EXECUTE_RUN_TASK = "runs.execute"
PROCESS_BATCH_TASK = "runs.process"

celery_app = Celery("idim", broker=get_settings().celery_broker_url)
celery_app.conf.update(
    task_default_queue=RUN_QUEUE,
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # RabbitMQ 4 rejects the transient non-exclusive queues Celery uses for remote control (pidbox);
    # we don't use remote control, gossip or mingle. Our task queue itself is durable.
    worker_enable_remote_control=False,
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
    return (retry_after or 0) + random.uniform(0, get_settings().run_pacing_spread_seconds)


def _delay(attempt: int, retry_after: float | None = None) -> float:
    settings = get_settings()
    return backoff_seconds(
        attempt,
        base=settings.run_retry_base_seconds,
        cap=settings.run_retry_max_seconds,
        retry_after=retry_after,
    )


@celery_app.task(name=EXECUTE_RUN_TASK, bind=True)
def execute_run_task(self, run_id: str, provider_errors: int = 0) -> None:
    from app.services.run_engine import discover, fail_run

    settings = get_settings()
    rid = uuid.UUID(run_id)
    try:
        items = _run_async(lambda sf, client: discover(rid, session_factory=sf, client=client))
    except QuotaExhausted as exc:
        # Our own budget is spent for this window: try again next window, without using an attempt.
        raise self.retry(
            countdown=_pacing_delay(exc.retry_after),
            max_retries=None,
            kwargs={"provider_errors": provider_errors},
        ) from exc
    except TransientError as exc:
        attempt = provider_errors
        if attempt + 1 >= settings.run_max_attempts:
            message = f"Couldn't list emails after {attempt + 1} attempts: {exc}"
            _run_async(lambda sf, _client: fail_run(sf, rid, message))
            return
        countdown = _delay(attempt, exc.retry_after)
        logger.warning("Run %s: listing deferred %.0fs (attempt %s): %s", run_id, countdown, attempt + 1, exc)
        # Re-publish this task to the broker with a delay; the worker process is freed immediately.
        raise self.retry(
            countdown=countdown, max_retries=None, kwargs={"provider_errors": attempt + 1}
        ) from exc

    size = settings.run_batch_size
    for start in range(0, len(items), size):
        batch = [item.to_message() for item in items[start : start + size]]
        process_batch_task.apply_async(args=[run_id, batch, 0])
    logger.info("Run %s: %s emails in %s batches", run_id, len(items), -(-len(items) // size))


@celery_app.task(name=PROCESS_BATCH_TASK)
def process_batch_task(run_id: str, items: list[list[str]], attempt: int = 0) -> None:
    from app.services.run_engine import WorkItem, process_batch

    settings = get_settings()
    rid = uuid.UUID(run_id)
    outcome = _run_async(
        lambda sf, client: process_batch(
            rid,
            [WorkItem.from_message(item) for item in items],
            attempt=attempt,
            max_attempts=settings.run_max_attempts,
            session_factory=sf,
            client=client,
        )
    )
    if outcome.paced:
        process_batch_task.apply_async(
            args=[run_id, [item.to_message() for item in outcome.paced], attempt],
            countdown=_pacing_delay(outcome.paced_after),
        )
    if outcome.deferred:
        countdown = _delay(attempt, outcome.retry_after)
        logger.info(
            "Run %s: re-queuing %s emails in %.0fs (attempt %s)",
            run_id,
            len(outcome.deferred),
            countdown,
            attempt + 2,
        )
        process_batch_task.apply_async(
            args=[run_id, [item.to_message() for item in outcome.deferred], attempt + 1], countdown=countdown
        )
