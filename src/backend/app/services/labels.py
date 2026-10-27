import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailLabel
from app.models.filter import Filter
from app.models.label import Label
from app.models.processor import Processor, processor_labels
from app.schemas.label import LabelCreate, LabelFilterRef, LabelProcessorRef, LabelRead, LabelUpdate


class LabelNameTakenError(Exception):
    pass


class DefaultLabelError(Exception):
    """Built-in default labels can't be deleted."""


class LabelInUseError(Exception):
    """A filter still writes this label, or a processor runs on it."""


def _email_count():
    """Correlated count of emails (across all inboxes) carrying a label."""
    return (
        select(func.count()).select_from(EmailLabel).where(EmailLabel.label_id == Label.id).scalar_subquery()
    )


async def _filters_by_label(
    session: AsyncSession, label_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[LabelFilterRef]]:
    result: dict[uuid.UUID, list[LabelFilterRef]] = {label_id: [] for label_id in label_ids}
    if not label_ids:
        return result
    rows = await session.execute(
        select(Filter.label_id, Filter.id, Filter.name, Filter.status)
        .where(Filter.label_id.in_(label_ids))
        .order_by(Filter.name)
    )
    for label_id, filter_id, name, status in rows:
        result[label_id].append(LabelFilterRef(id=filter_id, name=name, status=status.value))
    return result


async def _processors_by_label(
    session: AsyncSession, label_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[LabelProcessorRef]]:
    result: dict[uuid.UUID, list[LabelProcessorRef]] = {label_id: [] for label_id in label_ids}
    if not label_ids:
        return result
    rows = await session.execute(
        select(processor_labels.c.label_id, Processor.id, Processor.name, Processor.status)
        .join(Processor, Processor.id == processor_labels.c.processor_id)
        .where(processor_labels.c.label_id.in_(label_ids))
        .order_by(Processor.name)
    )
    for label_id, processor_id, name, status in rows:
        result[label_id].append(LabelProcessorRef(id=processor_id, name=name, status=status.value))
    return result


def _to_read(
    label: Label, email_count: int, filters: list[LabelFilterRef], processors: list[LabelProcessorRef]
) -> LabelRead:
    return LabelRead(
        id=label.id,
        name=label.name,
        display_name=label.display_name,
        color=label.color,  # type: ignore[arg-type]
        email_count=email_count,
        filters=filters,
        processors=processors,
        is_default=label.default_key is not None,
        created_at=label.created_at,
    )


async def list_labels(session: AsyncSession) -> list[LabelRead]:
    rows = (await session.execute(select(Label, _email_count()).order_by(Label.display_name))).all()
    ids = [label.id for label, _ in rows]
    filters = await _filters_by_label(session, ids)
    processors = await _processors_by_label(session, ids)
    return [_to_read(label, count, filters[label.id], processors[label.id]) for label, count in rows]


async def get_label(session: AsyncSession, label_id: uuid.UUID) -> LabelRead | None:
    row = (await session.execute(select(Label, _email_count()).where(Label.id == label_id))).first()
    if row is None:
        return None
    label, count = row
    return _to_read(
        label,
        count,
        (await _filters_by_label(session, [label.id]))[label.id],
        (await _processors_by_label(session, [label.id]))[label.id],
    )


async def create_label(session: AsyncSession, data: LabelCreate) -> LabelRead:
    label = Label(name=data.name, display_name=data.display_name, color=data.color)
    session.add(label)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise LabelNameTakenError(data.name) from exc
    await session.refresh(label)
    return _to_read(label, 0, [], [])


async def update_label(session: AsyncSession, label_id: uuid.UUID, data: LabelUpdate) -> LabelRead | None:
    label = await session.get(Label, label_id)
    if label is None:
        return None
    for field in data.model_fields_set:  # only the fields the client sent
        setattr(label, field, getattr(data, field))
    await session.commit()
    return await get_label(session, label_id)


async def delete_label(session: AsyncSession, label_id: uuid.UUID) -> bool:
    """Delete a label and remove it from every email. Refused while any filter writes it or any
    processor runs on it."""
    label = await session.get(Label, label_id)
    if label is None:
        return False
    if label.default_key is not None:
        raise DefaultLabelError(label.name)
    if await session.scalar(select(func.count()).select_from(Filter).where(Filter.label_id == label_id)):
        raise LabelInUseError(label.name)
    if await session.scalar(
        select(func.count()).select_from(processor_labels).where(processor_labels.c.label_id == label_id)
    ):
        raise LabelInUseError(label.name)
    await session.delete(label)
    await session.commit()
    return True
