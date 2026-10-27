"""Querying datasets (the records processors write) for dashboards. Queries are JSON shapes checked
against the dataset's declared fields, and turned into SQL over `records` only through those fields:
nothing from the client reaches SQL as text. Snapshot datasets are reduced to the latest record per key
(as of the range's end) before aggregating."""

from typing import Any

from sqlalchemy import Numeric, Select, func, literal, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.mail.sources import message_url
from app.models.email import Email
from app.models.inbox import Inbox
from app.models.processor import Record
from app.processors import kinds
from app.processors.records import DATASETS, Dataset, FieldRole
from app.schemas.dataset import (
    DatasetFieldRead,
    DatasetRead,
    FieldFilter,
    QueryScope,
    RecordEmail,
    RecordRead,
    RowsQuery,
    RowsResult,
    SeriesQuery,
    SeriesResult,
    SeriesRow,
)


class DatasetQueryError(Exception):
    """An unknown dataset or field, or a field used in a way its role doesn't allow. Safe to show."""


def datasets() -> list[DatasetRead]:
    kinds()  # importing the kinds defines their datasets
    return [
        DatasetRead(
            name=d.name,
            title=d.title,
            kind=d.kind,
            time_field=d.time_field,
            key_field=d.key_field,
            fields=[
                DatasetFieldRead(
                    name=f.name, title=f.title, type=f.type, role=f.role, description=f.description
                )
                for f in d.fields
            ],
        )
        for d in sorted(DATASETS.values(), key=lambda d: d.name)
    ]


def dataset_spec(name: str) -> Dataset:
    kinds()
    dataset = DATASETS.get(name)
    if dataset is None:
        raise DatasetQueryError(f"Unknown dataset {name!r}")
    return dataset


def check_field(dataset: Dataset, name: str, roles: tuple[FieldRole, ...], use: str) -> Any:
    field = dataset.field(name)
    if field is None:
        raise DatasetQueryError(f"{dataset.name} has no field {name!r}")
    if field.role not in roles:
        raise DatasetQueryError(f"{dataset.name}.{name} can't be used to {use}")
    return field


def _text(name: str) -> Any:
    return Record.data[name].astext


def _scoped(dataset: Dataset, scope: QueryScope, filters: list[FieldFilter]) -> Select:
    """The dataset's records in scope, as a subquery-able select of `records`."""
    conditions = [Record.dataset == dataset.name]
    if scope.processor_ids is not None:
        conditions.append(Record.processor_id.in_(scope.processor_ids))
    if scope.end is not None:
        conditions.append(Record.occurred_at < scope.end)
    for f in filters:
        check_field(dataset, f.field, (FieldRole.DIMENSION, FieldRole.TEXT), "filter on")
        match = _text(f.field).in_(f.values)
        conditions.append(match if f.op == "in" else ~match)
    query = select(Record).where(*conditions)
    if dataset.kind == "snapshot":
        # The latest record per key as of the range's end; the range's start doesn't apply.
        return query.ext(distinct_on(Record.key)).order_by(Record.key, Record.occurred_at.desc())
    if scope.start is not None:
        query = query.where(Record.occurred_at >= scope.start)
    return query


async def series(session: AsyncSession, query: SeriesQuery) -> SeriesResult:
    dataset = dataset_spec(query.dataset)
    rows = _scoped(dataset, query, query.filters).subquery()
    data = rows.c.data
    if query.agg == "count" or query.measure is None:
        value = func.count()
    else:
        check_field(dataset, query.measure, (FieldRole.MEASURE,), "aggregate")
        number = data[query.measure].astext.cast(Numeric)
        value = (
            func.array_agg(aggregate_order_by(number, rows.c.occurred_at.desc()))[1]
            if query.agg == "latest"
            else getattr(func, query.agg)(number)
        )
    bucket = (
        func.date_trunc(query.bucket, func.timezone("UTC", rows.c.occurred_at))
        if query.bucket is not None
        else None
    )
    group = None
    if query.group_by is not None:
        check_field(dataset, query.group_by, (FieldRole.DIMENSION, FieldRole.TEXT), "group by")
        group = data[query.group_by].astext
    statement = select(
        (bucket if bucket is not None else literal(None)).label("bucket"),
        (group if group is not None else literal(None)).label("group"),
        value.label("value"),
    ).select_from(rows)
    if keys := [c for c in (bucket, group) if c is not None]:
        statement = statement.group_by(*keys)
    if bucket is not None:
        statement = statement.order_by(bucket)
    elif group is not None:
        statement = statement.order_by(value.desc().nulls_last())
        if query.limit:
            statement = statement.limit(query.limit)
    result = await session.execute(statement)
    return SeriesResult(
        rows=[
            SeriesRow(
                bucket=bucket.replace(tzinfo=None) if bucket is not None else None,
                group=group,
                value=float(v) if v is not None else None,
            )
            for bucket, group, v in result
        ]
    )


async def rows(session: AsyncSession, query: RowsQuery) -> RowsResult:
    dataset = dataset_spec(query.dataset)
    records = _scoped(dataset, query, query.filters).subquery()
    total = await session.scalar(select(func.count()).select_from(records)) or 0
    result = await session.execute(
        select(
            records,
            Email.subject,
            Email.sent_at,
            Email.provider_message_id,
            Inbox.provider,
            Inbox.email_address,
        )
        .outerjoin(Email, Email.id == records.c.email_id)
        .outerjoin(Inbox, Inbox.id == Email.inbox_id)
        .order_by(records.c.occurred_at.desc(), records.c.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    items = []
    for row in result.mappings():
        email = None
        if row["email_id"] is not None and row["sent_at"] is not None:
            email = RecordEmail(
                id=row["email_id"],
                subject=row["subject"],
                sent_at=row["sent_at"],
                open_url=message_url(row["provider"], row["email_address"], row["provider_message_id"]),
            )
        items.append(
            RecordRead(
                id=row["id"],
                occurred_at=row["occurred_at"],
                processor_id=row["processor_id"],
                data=row["data"],
                email=email,
            )
        )
    return RowsResult(items=items, total=total, page=query.page, page_size=query.page_size)
