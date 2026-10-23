import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import EmailLabel
from app.models.label import Label
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate


class LabelNameTakenError(Exception):
    pass


def _to_read(label: Label, email_count: int) -> LabelRead:
    return LabelRead(
        id=label.id,
        name=label.name,
        description=label.description,
        color=label.color,  # type: ignore[arg-type]
        filter_condition=label.filter_condition,
        match_threshold=label.match_threshold,
        email_count=email_count,
        created_at=label.created_at,
    )


def _email_count():
    """Correlated count of emails (across all inboxes) carrying a label."""
    return (
        select(func.count()).select_from(EmailLabel).where(EmailLabel.label_id == Label.id).scalar_subquery()
    )


async def list_labels(session: AsyncSession) -> list[LabelRead]:
    rows = await session.execute(select(Label, _email_count()).order_by(Label.name))
    return [_to_read(label, email_count=count) for label, count in rows]


async def get_label(session: AsyncSession, label_id: uuid.UUID) -> LabelRead | None:
    label = await session.get(Label, label_id)
    if label is None:
        return None
    return _to_read(label, email_count=await _count_for(session, label.id))


async def _count_for(session: AsyncSession, label_id: uuid.UUID) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(EmailLabel).where(EmailLabel.label_id == label_id)
        )
        or 0
    )


async def create_label(session: AsyncSession, data: LabelCreate) -> LabelRead:
    label = Label(
        name=data.name,
        description=data.description,
        color=data.color,
        filter_condition=data.filter_condition,
        match_threshold=data.match_threshold,
    )
    session.add(label)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise LabelNameTakenError(data.name) from exc
    await session.refresh(label)
    return _to_read(label, email_count=0)


async def update_label(session: AsyncSession, label_id: uuid.UUID, data: LabelUpdate) -> LabelRead | None:
    label = await session.get(Label, label_id)
    if label is None:
        return None
    for field in data.model_fields_set:  # only the fields the client sent
        setattr(label, field, getattr(data, field))
    await session.commit()
    await session.refresh(label)
    return _to_read(label, email_count=await _count_for(session, label.id))


async def delete_label(session: AsyncSession, label_id: uuid.UUID) -> bool:
    """Delete a label. Once emails exist, the email_labels FK cascades so it is removed from all emails."""
    label = await session.get(Label, label_id)
    if label is None:
        return False
    await session.delete(label)
    await session.commit()
    return True
