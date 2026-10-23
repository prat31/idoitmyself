import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Granularity = Literal["day", "week", "month"]


class StatsTotals(BaseModel):
    emails: int
    labelled_emails: int
    label_assignments: int
    senders: int


class TimelineBucket(BaseModel):
    start: date  # first day of the bucket, in the requested timezone
    emails: int
    labelled: int


class LabelCount(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str
    emails: int


class InboxCount(BaseModel):
    inbox_id: uuid.UUID
    name: str
    email_address: str
    emails: int


class SenderCount(BaseModel):
    sender: str
    emails: int


class Overview(BaseModel):
    window_start: datetime | None
    window_end: datetime | None
    granularity: Granularity
    totals: StatsTotals
    timeline: list[TimelineBucket]
    by_label: list[LabelCount]
    by_inbox: list[InboxCount]
    top_senders: list[SenderCount]


class LabelStats(BaseModel):
    label_id: uuid.UUID
    granularity: Granularity
    emails: int
    emails_last_30_days: int
    avg_probability: float | None
    first_sent_at: datetime | None
    last_sent_at: datetime | None
    timeline: list[TimelineBucket]
    by_inbox: list[InboxCount]
    top_senders: list[SenderCount]


class EmailLabelRef(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str


class LabelledEmail(BaseModel):
    id: uuid.UUID
    inbox_id: uuid.UUID
    inbox_name: str
    sent_at: datetime
    from_address: str | None
    subject: str | None
    snippet: str | None
    probability: float
    run_id: uuid.UUID | None
    run_name: str | None
    other_labels: list[EmailLabelRef]


class EmailPage(BaseModel):
    items: list[LabelledEmail]
    total: int
    page: int
    page_size: int
