from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.scan import ScanScheduleUpdate
from app.services.scans import next_run_at, schedule_boundary

IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def scan_timezone(monkeypatch):
    def use(name: str) -> None:
        monkeypatch.setattr(get_settings(), "scan_timezone", name)

    use("Asia/Kolkata")
    return use


@pytest.mark.parametrize(
    ("now", "interval", "boundary"),
    [
        # 30 minutes and 1 hour: the same clock times in IST and UTC.
        (datetime(2026, 10, 25, 13, 0, tzinfo=UTC), 30, datetime(2026, 10, 25, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 25, 13, 29, 59, 999, tzinfo=UTC), 30, datetime(2026, 10, 25, 13, 0, tzinfo=UTC)),
        (datetime(2026, 10, 25, 13, 30, 1, tzinfo=UTC), 30, datetime(2026, 10, 25, 13, 30, tzinfo=UTC)),
        (datetime(2026, 10, 25, 13, 50, tzinfo=UTC), 60, datetime(2026, 10, 25, 13, 30, tzinfo=UTC)),
        # 3 hours, 6 hours and a day: from midnight IST.
        (datetime(2026, 10, 25, 17, 59, tzinfo=IST), 180, datetime(2026, 10, 25, 15, 0, tzinfo=IST)),
        (datetime(2026, 10, 25, 18, 0, tzinfo=IST), 180, datetime(2026, 10, 25, 18, 0, tzinfo=IST)),
        (datetime(2026, 10, 25, 11, 59, tzinfo=IST), 360, datetime(2026, 10, 25, 6, 0, tzinfo=IST)),
        (datetime(2026, 10, 25, 23, 59, tzinfo=IST), 1440, datetime(2026, 10, 25, 0, 0, tzinfo=IST)),
        (datetime(2026, 10, 25, 20, 0, tzinfo=UTC), 1440, datetime(2026, 10, 26, 0, 0, tzinfo=IST)),
    ],
)
def test_boundaries_count_from_midnight_in_the_scan_timezone(scan_timezone, now, interval, boundary):
    assert schedule_boundary(now, interval) == boundary
    assert schedule_boundary(now, interval).tzinfo == UTC


def test_another_timezone(scan_timezone):
    scan_timezone("UTC")
    now = datetime(2026, 10, 25, 4, 0, tzinfo=UTC)
    assert schedule_boundary(now, 1440) == datetime(2026, 10, 25, 0, 0, tzinfo=UTC)
    assert schedule_boundary(now, 180) == datetime(2026, 10, 25, 3, 0, tzinfo=UTC)


def test_next_run_is_the_following_boundary(scan_timezone):
    cases = [
        (datetime(2026, 10, 25, 13, 0, tzinfo=UTC), 30, datetime(2026, 10, 25, 13, 30, tzinfo=UTC)),
        (datetime(2026, 10, 25, 22, 10, tzinfo=IST), 180, datetime(2026, 10, 26, 0, 0, tzinfo=IST)),
        (datetime(2026, 10, 25, 9, 0, tzinfo=IST), 1440, datetime(2026, 10, 26, 0, 0, tzinfo=IST)),
    ]
    for now, interval, expected in cases:
        assert next_run_at(now, interval) == expected


def test_timezone_must_be_known():
    Settings(scan_timezone="Europe/London")  # fine
    with pytest.raises(ValidationError, match="unknown timezone"):
        Settings(scan_timezone="Mars/Olympus")


def test_only_offered_intervals():
    assert ScanScheduleUpdate(interval_minutes=360).interval_minutes == 360
    with pytest.raises(ValidationError):
        ScanScheduleUpdate(interval_minutes=45)
