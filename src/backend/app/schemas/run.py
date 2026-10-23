import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.run import RunKind, RunStatus


class AdhocRunCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    label_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    inbox_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    # The client converts its local-date range into instants: [window_start, window_end).
    window_start: datetime
    window_end: datetime
    # Re-ask the model even for (email, label) pairs already evaluated with the current condition.
    reclassify: bool = False

    @model_validator(mode="after")
    def check_window(self) -> Self:
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("window_start and window_end must include a timezone")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        self.label_ids = list(dict.fromkeys(self.label_ids))
        self.inbox_ids = list(dict.fromkeys(self.inbox_ids))
        return self


class RunLabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label_id: uuid.UUID | None
    label_name: str
    filter_condition: str
    match_threshold: float
    matched: int


class RunInboxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inbox_id: uuid.UUID | None
    inbox_name: str
    email_address: str
    emails_found: int
    error: str | None


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: RunKind
    status: RunStatus
    window_start: datetime
    window_end: datetime
    model: str
    reclassify: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    emails_found: int
    emails_processed: int
    emails_skipped: int
    emails_failed: int
    emails_matched: int
    labels_applied: int
    labels_removed: int
    retries: int
    cost_usd: Decimal
    labels: list[RunLabelRead]
    inboxes: list[RunInboxRead]


class RunCoverageRequest(BaseModel):
    label_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    inbox_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    window_start: datetime
    window_end: datetime


class CoveredRange(BaseModel):
    start: datetime
    end: datetime


class LabelCoverage(BaseModel):
    """How much of the requested window this label has already been evaluated over, for every
    selected inbox, with its current filter condition."""

    label_id: uuid.UUID
    label_name: str
    covered: list[CoveredRange]  # merged, clipped to the request window
    evaluated_emails: int  # stored emails in the window already answered for this label


class RunCoverage(BaseModel):
    labels: list[LabelCoverage]


class TimelineBucketOut(BaseModel):
    start: date
    emails: int


class ProbabilityBucket(BaseModel):
    start: float  # bucket covers [start, start + 0.1); the last one includes 1.0
    count: int


class RunLabelInsight(BaseModel):
    label_id: uuid.UUID | None
    label_name: str
    color: str | None  # None if the label was deleted
    filter_condition: str  # as this run asked it
    match_threshold: float  # as this run applied it
    condition_changed: bool  # the label's current condition differs (or the label is gone)
    asked: int  # (email, label) answers from the model still attributed to this run
    matched: int
    near_threshold: int  # answers within ±NEAR of the threshold
    histogram: list[ProbabilityBucket]


class RunInsights(BaseModel):
    near_window: float
    granularity: Literal["day", "week", "month"]
    labels: list[RunLabelInsight]
    matched_timeline: list[TimelineBucketOut]


class RunEmailLabel(BaseModel):
    label_id: uuid.UUID | None
    label_name: str
    color: str | None
    probability: float
    matched: bool
    from_this_run: bool  # False: answered by an earlier run and reused (skipped)


class RunEmailRow(BaseModel):
    email_id: uuid.UUID
    inbox_name: str
    sent_at: datetime
    from_address: str | None
    subject: str | None
    snippet: str | None
    result: RunEmailLabel


class RunEmailPage(BaseModel):
    items: list[RunEmailRow]
    total: int
    page: int
    page_size: int
