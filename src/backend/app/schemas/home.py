import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.scan import ScanRead


class LabelMonth(BaseModel):
    label_id: uuid.UUID
    display_name: str
    color: str
    this_month: int
    last_month: int


class HomeSummary(BaseModel):
    """Scan figures for the filtered range (by scan finish time), filter counts, and month-on-month
    labels."""

    scans_completed: int
    scans_failed: int
    emails_scanned: int  # new emails fetched and filtered (excludes ones already stored)
    emails_labelled: int  # emails that got at least one label (one email can get several)
    active_filters: int
    inactive_filters: int
    label_months: list[LabelMonth]


class AttentionFilter(BaseModel):
    filter_id: uuid.UUID
    name: str
    label_display_name: str


class AttentionLabel(BaseModel):
    label_id: uuid.UUID
    display_name: str
    color: str


class AttentionScan(BaseModel):
    scan_id: uuid.UUID
    inbox_name: str
    status: str
    emails_failed: int
    error: str | None
    created_at: datetime


class AttentionInbox(BaseModel):
    inbox_id: uuid.UUID
    name: str
    email_address: str
    error: str
    scan_id: uuid.UUID | None


class AttentionInput(BaseModel):
    """Processor runs waiting for something only the user can give (e.g. a PDF password)."""

    name: str  # what to save it as (with scope)
    scope: str
    prompt: str  # what to ask
    secret: bool  # a password or the like: typed hidden
    waiting_runs: int
    # A saved value didn't work (otherwise none is saved yet).
    wrong: bool
    # The latest waiting email, to open and check.
    email_subject: str | None
    email_sent_at: datetime
    open_url: str | None


class HomeAttention(BaseModel):
    inboxes_with_errors: list[AttentionInbox]  # the inbox's latest finished scan failed
    scans_with_problems: list[AttentionScan]  # failed, or completed with failed emails (last 30 days)
    filters_never_matched: list[AttentionFilter]  # active, but haven't labelled anything yet
    labels_without_active_filter: list[AttentionLabel]  # nothing adds them any more
    inboxes_without_filters: list[AttentionInbox]  # no active filter covers it, so it isn't scanned
    inputs_needed: list[AttentionInput]  # per input name and scope
    # Active, with AI conditions, but OPENROUTER_API_KEY isn't set: scans skip them.
    filters_skipped_without_ai_key: list[AttentionFilter]


class InboxStatus(BaseModel):
    inbox_id: uuid.UUID
    name: str
    email_address: str
    provider: str
    scanned_until: datetime | None  # end of the last scheduled scan's window
    last_completed_scan_at: datetime | None
    active_scan: ScanRead | None
    quota_used: int  # provider quota units reserved in the current budget window
    quota_limit: int
    quota_window_seconds: int


class HomeStatus(BaseModel):
    scan_interval_minutes: int
    inboxes: list[InboxStatus]


class RecentMatch(BaseModel):
    email_id: uuid.UUID
    sent_at: datetime
    from_address: str | None
    subject: str | None
    inbox_name: str
    label_id: uuid.UUID
    label_display_name: str
    label_color: str
    filter_name: str | None
    applied_at: datetime
    # Opens the message in the provider's web UI (null if the provider has none).
    open_url: str | None


class HomeRecent(BaseModel):
    matches: list[RecentMatch]
