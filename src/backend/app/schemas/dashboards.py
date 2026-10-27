import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.processor import ProcessorStatus
from app.schemas.dataset import Aggregation, Bucket, FieldFilter


class WidgetQuery(BaseModel):
    """What a widget shows (see SeriesQuery and RowsQuery). The page adds the processor and date range."""

    dataset: str
    measure: str | None = None
    agg: Aggregation = "sum"
    group_by: str | None = None
    bucket: Bucket | None = None
    filters: list[FieldFilter] = []
    limit: int | None = Field(default=None, ge=1, le=100)
    columns: list[str] | None = None  # tables: the fields to show, in order


class Widget(BaseModel):
    id: str
    # stat: one value (with the change vs the previous period); timeseries: a value per bucket;
    # composition: per bucket, stacked by group; breakdown: a value per group; table: records.
    type: Literal["stat", "timeseries", "composition", "breakdown", "table"]
    title: str
    description: str | None = None
    width: Literal["full", "half", "third"] = "half"
    query: WidgetQuery


class DashboardSpec(BaseModel):
    default_range: Literal["3m", "6m", "12m", "all"] = "12m"
    widgets: list[Widget]


class DashboardLabel(BaseModel):
    id: uuid.UUID
    display_name: str
    color: str


class DashboardRead(BaseModel):
    """A processor's dashboard: its kind's default spec, over that processor's records."""

    id: uuid.UUID  # the processor's id
    name: str
    description: str | None
    processor_status: ProcessorStatus
    kind: str
    kind_name: str
    labels: list[DashboardLabel]
    spec: DashboardSpec
