import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EmailSort = Literal["sent_desc", "sent_asc", "sender_asc", "sender_desc", "subject_asc", "subject_desc"]


class EmailLabelTag(BaseModel):
    label_id: uuid.UUID
    display_name: str
    color: str
    filter_name: str | None  # the filter that added it (null if deleted since)


class EmailRow(BaseModel):
    id: uuid.UUID
    inbox_id: uuid.UUID
    inbox_name: str
    sent_at: datetime
    from_address: str | None
    to_addresses: str | None
    subject: str | None
    snippet: str | None
    labels: list[EmailLabelTag]
    scanned_at: datetime
    # Opens the message in the provider's web UI (null if the provider has none).
    open_url: str | None


class EmailListStats(BaseModel):
    """Over every email matching the filters (not just the page)."""

    emails: int
    labelled: int
    unlabelled: int
    senders: int
    inboxes: int
    first_sent_at: datetime | None
    last_sent_at: datetime | None


class EmailList(BaseModel):
    items: list[EmailRow]
    total: int
    page: int
    page_size: int
    stats: EmailListStats
