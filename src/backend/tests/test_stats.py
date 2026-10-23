from datetime import date, timedelta

import pytest

from app.services.stats import StatsQueryError, bucket_start, choose_granularity, fill_buckets, parse_timezone


@pytest.mark.parametrize(
    ("days", "expected"),
    [(1, "day"), (45, "day"), (46, "week"), (200, "week"), (201, "month"), (3650, "month")],
)
def test_granularity_by_span(days, expected):
    assert choose_granularity(timedelta(days=days)) == expected


def test_bucket_start_matches_postgres_date_trunc():
    thursday = date(2026, 10, 15)
    assert bucket_start(thursday, "day") == thursday
    assert bucket_start(thursday, "week") == date(2026, 10, 12)  # Monday
    assert bucket_start(thursday, "month") == date(2026, 10, 1)


def test_fill_buckets_is_continuous_and_zero_filled():
    buckets = fill_buckets({date(2026, 10, 2): (5, 2)}, date(2026, 10, 1), date(2026, 10, 3), "day")
    assert [(b.start.day, b.emails, b.labelled) for b in buckets] == [(1, 0, 0), (2, 5, 2), (3, 0, 0)]


def test_fill_buckets_months_cross_year():
    buckets = fill_buckets({}, date(2025, 11, 20), date(2026, 2, 3), "month")
    assert [b.start for b in buckets] == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]


def test_unknown_timezone_rejected():
    assert parse_timezone("Asia/Kolkata").key == "Asia/Kolkata"
    with pytest.raises(StatsQueryError):
        parse_timezone("Mars/Olympus")
