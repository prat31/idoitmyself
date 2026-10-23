import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Granularity = Literal["day", "week", "month"]


class SpendBucket(BaseModel):
    start: date
    cost_usd: Decimal
    emails: int  # emails sent to the model


class LabelMonth(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str
    this_month: int
    last_month: int


class DashboardSummary(BaseModel):
    """Run and spend figures for the filtered range (by run finish time), plus month-on-month labels."""

    runs_completed: int
    runs_failed: int
    cost_usd: Decimal
    emails_sent_to_model: int
    emails_skipped: int
    estimated_saved_usd: Decimal  # skipped emails × average model cost per classified email
    spend_granularity: Granularity
    spend: list[SpendBucket]
    label_months: list[LabelMonth]


class AttentionLabel(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str
    count: int | None = None  # meaning depends on the list


class AttentionRun(BaseModel):
    run_id: uuid.UUID
    name: str
    status: str
    emails_failed: int
    error: str | None
    created_at: datetime


class AttentionInbox(BaseModel):
    inbox_id: uuid.UUID
    name: str
    email_address: str
    error: str
    run_id: uuid.UUID


class DashboardAttention(BaseModel):
    labels_without_condition: list[AttentionLabel]
    labels_stale: list[AttentionLabel]  # condition edited since the last completed run (count unused)
    labels_never_run: list[AttentionLabel]
    labels_near_threshold: list[AttentionLabel]  # count = current answers within ±near of threshold
    labels_likely_misses: list[AttentionLabel]  # count = current answers just below threshold
    near_window: float
    runs_with_problems: list[AttentionRun]  # failed, or completed with failed emails (last 30 days)
    inboxes_with_errors: list[AttentionInbox]  # latest listing error per inbox


class InboxStatus(BaseModel):
    inbox_id: uuid.UUID
    name: str
    email_address: str
    last_scanned_at: datetime | None  # last completed run that covered this inbox
    scanned_since: datetime | None  # earliest window start covered by a completed run
    quota_used: int  # Gmail quota units reserved in the current budget window
    quota_limit: int
    quota_window_seconds: int


class DashboardStatus(BaseModel):
    inboxes: list[InboxStatus]


class CoveredSpan(BaseModel):
    start: datetime
    end: datetime


class LabelCoverageRow(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str
    covered: list[CoveredSpan]  # merged ranges covered in every connected inbox, current condition


class DashboardCoverage(BaseModel):
    span_start: datetime | None
    span_end: datetime
    labels: list[LabelCoverageRow]


class RecentMatch(BaseModel):
    email_id: uuid.UUID
    sent_at: datetime
    from_address: str | None
    subject: str | None
    inbox_name: str
    label_id: uuid.UUID
    label_name: str
    color: str
    probability: float
    labelled_at: datetime


class DashboardRecent(BaseModel):
    matches: list[RecentMatch]
