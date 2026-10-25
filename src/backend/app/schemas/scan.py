import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.models.scan import ScanKind, ScanStatus


class ScanFilterRef(BaseModel):
    id: uuid.UUID
    name: str


class ScanRead(BaseModel):
    id: uuid.UUID
    inbox_id: uuid.UUID
    inbox_name: str
    inbox_email_address: str
    kind: ScanKind
    status: ScanStatus
    window_start: datetime | None
    window_end: datetime | None
    started_at: datetime | None
    discovered_at: datetime | None
    finished_at: datetime | None
    error: str | None
    emails_found: int
    emails_processed: int
    emails_skipped: int
    emails_failed: int
    emails_matched: int
    labels_applied: int
    retries: int
    # Ad hoc scans: the filters they run.
    filters: list[ScanFilterRef]
    created_at: datetime
    updated_at: datetime


class ScanPage(BaseModel):
    items: list[ScanRead]
    total: int
    page: int
    page_size: int


class AdhocScanCreate(BaseModel):
    """Run chosen active filters over emails received in [window_start, window_end), in every inbox
    their scopes cover. Only emails no scan has stored yet are read, and each inbox's range is clipped
    to end where scheduled scans take over for it; the range must be in the past (an end in the future
    is clipped to now)."""

    filter_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=50)]
    window_start: datetime
    window_end: datetime

    @model_validator(mode="after")
    def ordered(self) -> "AdhocScanCreate":
        self.filter_ids = list(dict.fromkeys(self.filter_ids))
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class ScanSchedule(BaseModel):
    """When scheduled scans run: every `interval_minutes` from the hour; the next tick is `next_run_at`."""

    interval_minutes: int
    next_run_at: datetime
