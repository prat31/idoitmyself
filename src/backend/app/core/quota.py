"""Client-side budgeting of a provider's per-user API quota, shared by every worker process via Redis.

We reserve a call's cost *before* making it; when the current window's budget is spent we don't call
the provider at all — the caller re-queues the work for the next window. This keeps us under the
provider's limit instead of discovering it through 403/429 refusals (which Google may start billing
for)."""

import time
from typing import Protocol

from app.core.retry import TransientError


class QuotaExhausted(TransientError):
    """Our own budget for this window is spent. Not a failure: re-queue without using an attempt."""


class _Counter(Protocol):
    async def incrby(self, name: str, amount: int) -> int: ...
    async def decrby(self, name: str, amount: int) -> int: ...
    async def expire(self, name: str, time: int) -> bool: ...


class QuotaBudget:
    """Fixed windows of `window_seconds`, each allowed `units_per_minute * utilisation * window/60`
    units. Short windows spread calls evenly through the minute rather than bursting at its start."""

    def __init__(
        self,
        counter: _Counter,
        *,
        namespace: str,
        units_per_minute: int,
        utilisation: float,
        window_seconds: int,
        clock=time.time,
    ):
        self._counter = counter
        self._namespace = namespace
        self._window = window_seconds
        self._limit = max(1, int(units_per_minute * utilisation * window_seconds / 60))
        self._clock = clock

    @property
    def units_per_window(self) -> int:
        return self._limit

    async def reserve(self, subject: str, units: int) -> None:
        """Reserve `units` for `subject` (e.g. a mailbox) or raise QuotaExhausted with the seconds
        until the next window."""
        now = self._clock()
        window = int(now // self._window)
        key = f"quota:{self._namespace}:{subject}:{window}"
        used = await self._counter.incrby(key, units)
        if used == units:
            await self._counter.expire(key, self._window * 3)
        if used > self._limit:
            await self._counter.decrby(key, units)  # give back: the call won't be made
            raise QuotaExhausted(
                f"{self._namespace} quota budget used ({self._limit} units per {self._window}s window)",
                retry_after=(window + 1) * self._window - now,
            )
