import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

from app.models.processor import ProcessorRunStatus, ProcessorStatus
from app.schemas.dataset import DatasetRead

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ProcessorKindRead(BaseModel):
    """A kind from the code: what it writes, and its settings (JSON schema), if any."""

    key: str
    name: str
    description: str
    version: int
    writes: list[DatasetRead]
    config_schema: dict[str, Any] | None
    has_dashboard: bool


class ProcessorLabel(BaseModel):
    id: uuid.UUID
    display_name: str
    color: str


class ProcessorRunCounts(BaseModel):
    active: int  # queued or running
    succeeded: int
    skipped: int
    failed: int
    needs_input: int


class ProcessorRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    labels: list[ProcessorLabel]
    kind: str
    kind_name: str
    config: dict[str, Any]
    status: ProcessorStatus
    status_changed_at: datetime
    created_at: datetime
    runs: ProcessorRunCounts
    last_run_at: datetime | None
    records: int  # records it has written, in every dataset
    has_dashboard: bool
    # A built-in default: editable and can be deactivated, but not deleted.
    is_default: bool


class ProcessorCreate(BaseModel):
    """New processors start active. The kind can't change afterwards; the labels can."""

    name: Name
    description: Description | None = None
    label_ids: list[uuid.UUID] = Field(min_length=1)
    kind: str
    config: dict[str, Any] = {}


class ProcessorUpdate(BaseModel):
    name: Name | None = None
    description: Description | None = None
    label_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    config: dict[str, Any] | None = None
    status: ProcessorStatus | None = None


class ProcessorRunRead(BaseModel):
    id: uuid.UUID
    status: ProcessorRunStatus
    error: str | None
    attempts: int
    records_written: int
    input_name: str | None
    input_scope: str | None
    input_prompt: str | None
    created_at: datetime
    finished_at: datetime | None
    email_id: uuid.UUID
    sent_at: datetime
    from_address: str | None
    subject: str | None
    inbox_name: str
    # Opens the message in the provider's web UI (null if the provider has none).
    open_url: str | None


class ProcessorRunPage(BaseModel):
    items: list[ProcessorRunRead]
    total: int
    page: int
    page_size: int


class QueuedRuns(BaseModel):
    queued: int


class InputSave(BaseModel):
    """A value a processor asked for (e.g. a PDF password), for one name and scope. Stored encrypted,
    never returned."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    scope: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    value: Annotated[str, StringConstraints(min_length=1, max_length=500)]
