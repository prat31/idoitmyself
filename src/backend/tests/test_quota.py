import pytest

from app.core.quota import QuotaBudget, QuotaExhausted
from tests.fakes import MemoryCounter


def budget(clock, counter=None) -> QuotaBudget:
    # 6,000 units/min at 90% in 10s windows → 900 units per window (15 full Gmail fetches).
    return QuotaBudget(
        counter or MemoryCounter(),
        namespace="gmail",
        units_per_minute=6000,
        utilisation=0.9,
        window_seconds=10,
        clock=clock,
    )


async def test_window_allows_its_share_then_paces():
    b = budget(lambda: 1000.0)
    assert b.units_per_window == 900
    for _ in range(15):
        await b.reserve("inbox-1", 60)
    with pytest.raises(QuotaExhausted) as caught:
        await b.reserve("inbox-1", 60)
    assert caught.value.retry_after == pytest.approx(10.0)  # 1000 → next window at 1010


async def test_refused_reservation_is_given_back_and_small_calls_still_fit():
    b = budget(lambda: 1000.0)
    for _ in range(14):
        await b.reserve("inbox-1", 60)  # 840 used
    with pytest.raises(QuotaExhausted):
        await b.reserve("inbox-1", 100)  # would be 940: refused and returned
    await b.reserve("inbox-1", 60)  # 900: exactly fits


async def test_budget_is_per_mailbox_and_resets_each_window():
    now = [1000.0]
    counter = MemoryCounter()
    b = budget(lambda: now[0], counter)
    for _ in range(15):
        await b.reserve("inbox-1", 60)
    await b.reserve("inbox-2", 60)  # another mailbox has its own budget
    now[0] = 1010.0
    await b.reserve("inbox-1", 60)  # new window
