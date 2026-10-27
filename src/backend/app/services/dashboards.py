"""Dashboards. For now each processor whose kind ships a default dashboard (app.processors kinds'
`dashboard`) has one: the kind's spec over that processor's records. Specs are checked against the
datasets when loaded."""

import uuid
from functools import cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processor import Processor
from app.processors import kinds
from app.processors.records import FieldRole
from app.schemas.dashboards import DashboardLabel, DashboardRead, DashboardSpec
from app.services.datasets import DatasetQueryError, check_field, dataset_spec


def check_spec(spec: DashboardSpec) -> None:
    """Raise DatasetQueryError if a widget names an unknown dataset or field, or misuses one."""
    for widget in spec.widgets:
        query = widget.query
        dataset = dataset_spec(query.dataset)
        if query.measure is not None:
            check_field(dataset, query.measure, (FieldRole.MEASURE,), "aggregate")
        if query.group_by is not None:
            check_field(dataset, query.group_by, (FieldRole.DIMENSION, FieldRole.TEXT), "group by")
        for f in query.filters:
            check_field(dataset, f.field, (FieldRole.DIMENSION, FieldRole.TEXT), "filter on")
        for column in query.columns or []:
            if dataset.field(column) is None:
                raise DatasetQueryError(f"{widget.id}: {dataset.name} has no field {column!r}")
        if widget.type in ("timeseries", "composition") and query.bucket is None:
            raise DatasetQueryError(f"{widget.id}: a {widget.type} needs a bucket")
        if widget.type in ("composition", "breakdown") and query.group_by is None:
            raise DatasetQueryError(f"{widget.id}: a {widget.type} needs group_by")


@cache
def kind_spec(kind_key: str) -> DashboardSpec | None:
    kind = kinds().get(kind_key)
    raw = kind.dashboard_spec() if kind else None
    if raw is None:
        return None
    spec = DashboardSpec.model_validate(raw)
    check_spec(spec)
    return spec


def _to_read(processor: Processor, spec: DashboardSpec) -> DashboardRead:
    kind = kinds().get(processor.kind)
    return DashboardRead(
        id=processor.id,
        name=processor.name,
        description=processor.description,
        processor_status=processor.status,
        kind=processor.kind,
        kind_name=kind.name if kind else processor.kind,
        labels=[
            DashboardLabel(id=label.id, display_name=label.display_name, color=label.color)
            for label in processor.labels
        ],
        spec=spec,
    )


async def list_dashboards(session: AsyncSession) -> list[DashboardRead]:
    result: list[DashboardRead] = []
    for processor in await session.scalars(select(Processor).order_by(Processor.name)):
        if (spec := kind_spec(processor.kind)) is not None:
            result.append(_to_read(processor, spec))
    return result


async def get_dashboard(session: AsyncSession, processor_id: uuid.UUID) -> DashboardRead | None:
    processor = await session.get(Processor, processor_id)
    spec = kind_spec(processor.kind) if processor else None
    return _to_read(processor, spec) if processor and spec else None
