import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.run import AdhocRunCreate

LABEL_ID, INBOX_ID = uuid.uuid4(), uuid.uuid4()


def test_valid_request_dedupes_ids():
    run = AdhocRunCreate(
        name="  September bills ",
        label_ids=[LABEL_ID, LABEL_ID],
        inbox_ids=[INBOX_ID],
        window_start=datetime(2026, 10, 1, tzinfo=UTC),
        window_end=datetime(2026, 10, 2, tzinfo=UTC),
    )
    assert run.label_ids == [LABEL_ID]
    assert run.name == "September bills"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"name": "x" * 101},
        {"label_ids": []},
        {"inbox_ids": []},
        {"window_end": datetime(2026, 10, 1, tzinfo=UTC)},  # not after start
        {"window_start": datetime(2026, 10, 1)},  # naive
    ],
)
def test_invalid_requests(overrides):
    data = {
        "name": "Run",
        "label_ids": [LABEL_ID],
        "inbox_ids": [INBOX_ID],
        "window_start": datetime(2026, 10, 1, tzinfo=UTC),
        "window_end": datetime(2026, 10, 2, tzinfo=UTC),
        **overrides,
    }
    with pytest.raises(ValidationError):
        AdhocRunCreate(**data)


def test_merge_and_intersect_ranges():
    from app.services.runs import intersect_all, merge_ranges

    d = lambda day: datetime(2026, 10, day, tzinfo=UTC)  # noqa: E731
    assert merge_ranges([(d(5), d(8)), (d(1), d(3)), (d(3), d(6))]) == [(d(1), d(8))]
    a = merge_ranges([(d(1), d(10))])
    b = merge_ranges([(d(3), d(5)), (d(8), d(12))])
    assert intersect_all([a, b]) == [(d(3), d(5)), (d(8), d(10))]
    assert intersect_all([a, []]) == []
