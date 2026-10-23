"""Transient-failure signalling and back-off. Workers never sleep on a retry: a transient error
propagates up to the Celery task, which re-publishes the work to the broker with a delay."""

import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


class TransientError(Exception):
    """A failure worth retrying later (rate limit, 5xx, network). `retry_after` is the server's hint
    in seconds, if it gave one."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def backoff_seconds(attempt: int, *, base: float, cap: float, retry_after: float | None = None) -> float:
    """Exponential back-off with full jitter for the given (0-based) attempt, never shorter than the
    server's Retry-After hint and never longer than `cap`."""
    exponential = min(cap, base * 2**attempt)
    delay = random.uniform(exponential / 2, exponential)
    if retry_after is not None:
        delay = max(delay, retry_after)
    return min(cap, delay)


def parse_retry_after(value: str | None) -> float | None:
    """Retry-After header: delta-seconds or an HTTP date."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError):
        return None
