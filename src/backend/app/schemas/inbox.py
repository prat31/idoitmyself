import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.inbox import InboxProvider
from app.models.scan import ScanKind, ScanStatus

TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class InboxLatestScan(BaseModel):
    id: uuid.UUID
    kind: ScanKind
    status: ScanStatus
    error: str | None
    emails_found: int
    emails_processed: int
    created_at: datetime
    finished_at: datetime | None


class InboxRead(BaseModel):
    id: uuid.UUID
    provider: InboxProvider  # the mailbox type
    name: str
    email_address: str
    notes: str | None
    tags: list[TagRead]
    connected_at: datetime
    created_at: datetime
    # Active filters whose scope covers this inbox (by its mailbox type or by name).
    active_filters: int
    # End of the last scheduled scan's window (null: never scanned on schedule).
    scanned_until: datetime | None
    last_scan: InboxLatestScan | None


class InboxDraft(BaseModel):
    """User-supplied details for a new inbox, carried through the OAuth round trip."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    tags: list[TagName] = Field(default_factory=list, max_length=20)
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None

    @field_validator("tags")
    @classmethod
    def dedupe_tags(cls, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for tag in tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique.append(tag)
        return unique

    @field_validator("notes")
    @classmethod
    def empty_notes_to_none(cls, notes: str | None) -> str | None:
        return notes or None


class AuthorizationUrl(BaseModel):
    authorization_url: str
