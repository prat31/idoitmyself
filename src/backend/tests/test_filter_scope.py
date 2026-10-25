import uuid

import pytest
from pydantic import ValidationError

from app.models.filter import Filter, FilterMailboxType
from app.models.inbox import Inbox, InboxProvider
from app.schemas.filter import FilterScope


def inbox() -> Inbox:
    return Inbox(id=uuid.uuid4(), provider=InboxProvider.GMAIL, name="i", email_address="i@x.com")


def test_scope_needs_an_entry_and_drops_duplicates():
    with pytest.raises(ValidationError):
        FilterScope()
    one = uuid.uuid4()
    scope = FilterScope(mailbox_types=["gmail", "gmail"], inbox_ids=[one, one])
    assert scope.mailbox_types == [InboxProvider.GMAIL] and scope.inbox_ids == [one]


def test_type_scope_covers_every_inbox_of_the_type():
    f = Filter(mailbox_types=[FilterMailboxType(mailbox_type=InboxProvider.GMAIL)], inboxes=[])
    assert f.covers(inbox()) and f.covers(inbox())


def test_inbox_scope_covers_only_chosen_inboxes():
    chosen, other = inbox(), inbox()
    f = Filter(mailbox_types=[], inboxes=[chosen])
    assert f.covers(chosen) and not f.covers(other)


def test_adhoc_request_needs_an_ordered_range_and_dedupes_filters():
    from datetime import UTC, datetime

    from app.schemas.scan import AdhocScanCreate

    one = uuid.uuid4()
    start, end = datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
    request = AdhocScanCreate(filter_ids=[one, one], window_start=start, window_end=end)
    assert request.filter_ids == [one]
    with pytest.raises(ValidationError):
        AdhocScanCreate(filter_ids=[one], window_start=end, window_end=start)
    with pytest.raises(ValidationError):
        AdhocScanCreate(filter_ids=[], window_start=start, window_end=end)
