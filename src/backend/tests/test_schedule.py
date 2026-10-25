from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.scans import schedule_boundary


@pytest.mark.parametrize(
    ("now", "boundary"),
    [
        (datetime(2026, 10, 25, 13, 0, 0, tzinfo=UTC), datetime(2026, 10, 25, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 25, 13, 29, 59, 999, tzinfo=UTC), datetime(2026, 10, 25, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 25, 13, 30, 1, tzinfo=UTC), datetime(2026, 10, 25, 13, 30, tzinfo=UTC)),
        (datetime(2026, 10, 25, 23, 59, 59, tzinfo=UTC), datetime(2026, 10, 25, 23, 30, tzinfo=UTC)),
    ],
)
def test_boundaries_fall_on_the_hour_and_half_hour(now, boundary):
    assert schedule_boundary(now) == boundary


def test_interval_must_divide_an_hour():
    Settings(scan_interval_minutes=15)  # fine
    with pytest.raises(ValidationError):
        Settings(scan_interval_minutes=7)


def test_next_run_is_the_following_boundary():
    from app.services.scans import next_run_at

    assert next_run_at(datetime(2026, 10, 25, 13, 0, tzinfo=UTC)) == datetime(
        2026, 10, 25, 13, 30, tzinfo=UTC
    )
    assert next_run_at(datetime(2026, 10, 25, 13, 47, tzinfo=UTC)) == datetime(
        2026, 10, 25, 14, 0, tzinfo=UTC
    )
