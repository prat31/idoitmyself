import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.processors.records import FieldRole, FieldType


class DatasetFieldRead(BaseModel):
    name: str
    title: str
    type: FieldType
    role: FieldRole
    description: str | None


class DatasetRead(BaseModel):
    name: str
    title: str
    kind: Literal["event", "snapshot"]
    time_field: str
    key_field: str | None
    fields: list[DatasetFieldRead]


class FieldFilter(BaseModel):
    field: str
    op: Literal["in", "not_in"] = "in"
    values: list[str] = Field(min_length=1)


Aggregation = Literal["sum", "avg", "min", "max", "count", "latest"]
Bucket = Literal["day", "week", "month", "year"]


class QueryScope(BaseModel):
    """Where a widget's data comes from, set by the page showing it: a processor's dashboard narrows to
    that processor; a date range narrows by the dataset's time field."""

    processor_ids: list[uuid.UUID] | None = None
    start: datetime | None = None
    end: datetime | None = None


class SeriesQuery(QueryScope):
    """An aggregate over one dataset: one value, or one per group and/or time bucket."""

    dataset: str
    measure: str | None = None  # None: count records
    agg: Aggregation = "sum"
    group_by: str | None = None
    bucket: Bucket | None = None
    filters: list[FieldFilter] = []
    limit: int | None = Field(default=None, ge=1, le=100)  # top groups by value


class SeriesRow(BaseModel):
    bucket: datetime | None
    group: str | None
    value: float | None


class SeriesResult(BaseModel):
    rows: list[SeriesRow]


class RowsQuery(QueryScope):
    """Records of one dataset, newest first, for tables."""

    dataset: str
    filters: list[FieldFilter] = []
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class RecordEmail(BaseModel):
    id: uuid.UUID
    subject: str | None
    sent_at: datetime
    open_url: str | None


class RecordRead(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    processor_id: uuid.UUID | None
    data: dict[str, Any]
    email: RecordEmail | None


class RowsResult(BaseModel):
    items: list[RecordRead]
    total: int
    page: int
    page_size: int
