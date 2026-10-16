import re
import uuid
from collections.abc import Collection

from sqlalchemy import case, delete, exists, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, InvalidRequestError, NotFoundError
from app.models.item import Item
from app.models.label import UNLABELED_SLUG, AssignedBy, ItemLabel, Label, LabelKind
from app.schemas.label import LabelCreate, LabelUpdate


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise InvalidRequestError("Label name must contain at least one letter or digit")
    return slug


# --- Labels -----------------------------------------------------------------------------


async def list_labels(
    session: AsyncSession, *, kind: LabelKind | None = None
) -> list[tuple[Label, int]]:
    """All labels with their item counts; system labels first, then by name."""
    query = (
        select(Label, func.count(ItemLabel.item_id))
        .outerjoin(ItemLabel, ItemLabel.label_id == Label.id)
        .group_by(Label.id)
        .order_by(case((Label.kind == LabelKind.SYSTEM, 0), else_=1), func.lower(Label.name))
    )
    if kind is not None:
        query = query.where(Label.kind == kind)
    rows = await session.execute(query)
    return [(label, count) for label, count in rows]


async def get_label(session: AsyncSession, label_id: uuid.UUID) -> Label:
    label = await session.get(Label, label_id)
    if label is None:
        raise NotFoundError(f"Label {label_id} not found")
    return label


async def count_items(session: AsyncSession, label_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(ItemLabel).where(ItemLabel.label_id == label_id)
    return await session.scalar(query) or 0


async def _ensure_slug_available(
    session: AsyncSession, slug: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    query = select(Label.id).where(Label.slug == slug)
    if exclude_id is not None:
        query = query.where(Label.id != exclude_id)
    if await session.scalar(query) is not None:
        raise ConflictError(f"A label named like '{slug}' already exists")


async def create_label(session: AsyncSession, data: LabelCreate) -> Label:
    slug = slugify(data.name)
    await _ensure_slug_available(session, slug)
    label = Label(
        name=data.name.strip(),
        slug=slug,
        kind=LabelKind.CUSTOM,
        color=data.color,
        description=data.description,
    )
    session.add(label)
    await session.commit()
    return label


def _ensure_custom(label: Label) -> None:
    if label.kind == LabelKind.SYSTEM:
        raise ForbiddenError(f"System label '{label.slug}' cannot be modified or deleted")


async def update_label(session: AsyncSession, label_id: uuid.UUID, data: LabelUpdate) -> Label:
    label = await get_label(session, label_id)
    _ensure_custom(label)
    changes = data.model_dump(exclude_unset=True)

    if "name" in changes:
        if changes["name"] is None:
            raise InvalidRequestError("Label name cannot be null")
        slug = slugify(changes["name"])
        await _ensure_slug_available(session, slug, exclude_id=label.id)
        label.name = changes["name"].strip()
        label.slug = slug
    if "color" in changes:
        label.color = changes["color"]
    if "description" in changes:
        label.description = changes["description"]

    await session.commit()
    return label


async def delete_label(session: AsyncSession, label_id: uuid.UUID) -> None:
    """Delete a custom label; items left without labels fall back to "unlabeled"."""
    label = await get_label(session, label_id)
    _ensure_custom(label)
    item_ids = list(
        await session.scalars(select(ItemLabel.item_id).where(ItemLabel.label_id == label.id))
    )
    await session.execute(delete(Label).where(Label.id == label.id))
    await ensure_labeled(session, item_ids)
    await session.commit()


# --- Item labels ------------------------------------------------------------------------


async def _unlabeled_id(session: AsyncSession) -> uuid.UUID:
    label_id = await session.scalar(select(Label.id).where(Label.slug == UNLABELED_SLUG))
    if label_id is None:
        raise RuntimeError("System label 'unlabeled' is missing; run database migrations")
    return label_id


async def ensure_labeled(session: AsyncSession, item_ids: Collection[uuid.UUID]) -> None:
    """Give the "unlabeled" label to any of these items that has no labels. Does not commit."""
    if not item_ids:
        return
    unlabeled_id = await _unlabeled_id(session)
    has_label = exists().where(ItemLabel.item_id == Item.id)
    await session.execute(
        insert(ItemLabel)
        .from_select(
            ["item_id", "label_id", "assigned_by"],
            select(Item.id, literal(unlabeled_id), literal(AssignedBy.SYSTEM.value)).where(
                Item.id.in_(item_ids), ~has_label
            ),
        )
        .on_conflict_do_nothing()
    )


async def _get_assignable_labels(
    session: AsyncSession, label_ids: Collection[uuid.UUID]
) -> list[Label]:
    labels = list(await session.scalars(select(Label).where(Label.id.in_(label_ids))))
    missing = set(label_ids) - {label.id for label in labels}
    if missing:
        raise NotFoundError(f"Label(s) not found: {', '.join(sorted(map(str, missing)))}")
    if any(label.slug == UNLABELED_SLUG for label in labels):
        raise InvalidRequestError(
            "The 'unlabeled' label is managed automatically and cannot be assigned"
        )
    return labels


async def _ensure_item_exists(session: AsyncSession, item_id: uuid.UUID) -> None:
    if await session.scalar(select(Item.id).where(Item.id == item_id)) is None:
        raise NotFoundError(f"Item {item_id} not found")


async def add_item_label(
    session: AsyncSession,
    item_id: uuid.UUID,
    label_id: uuid.UUID,
    *,
    assigned_by: AssignedBy = AssignedBy.MANUAL,
    confidence: float | None = None,
) -> None:
    """Attach a label to an item. Re-adding updates who assigned it (latest wins)."""
    if confidence is not None and not 0 <= confidence <= 1:
        raise InvalidRequestError("Confidence must be between 0 and 1")
    await _ensure_item_exists(session, item_id)
    await _get_assignable_labels(session, [label_id])

    values = {"assigned_by": assigned_by, "confidence": confidence}
    await session.execute(
        insert(ItemLabel)
        .values(item_id=item_id, label_id=label_id, **values)
        .on_conflict_do_update(
            index_elements=["item_id", "label_id"], set_={**values, "assigned_at": func.now()}
        )
    )
    await session.execute(
        delete(ItemLabel).where(
            ItemLabel.item_id == item_id, ItemLabel.label_id == await _unlabeled_id(session)
        )
    )
    await session.commit()


async def remove_item_label(session: AsyncSession, item_id: uuid.UUID, label_id: uuid.UUID) -> None:
    """Detach a label from an item; it falls back to "unlabeled" if none remain."""
    await _ensure_item_exists(session, item_id)
    if label_id == await _unlabeled_id(session):
        raise InvalidRequestError("The 'unlabeled' label is managed automatically")

    result = await session.execute(
        delete(ItemLabel).where(ItemLabel.item_id == item_id, ItemLabel.label_id == label_id)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise NotFoundError(f"Item {item_id} does not have label {label_id}")
    await ensure_labeled(session, [item_id])
    await session.commit()


async def set_item_labels(
    session: AsyncSession,
    item_id: uuid.UUID,
    label_ids: Collection[uuid.UUID],
    *,
    assigned_by: AssignedBy = AssignedBy.MANUAL,
) -> None:
    """Replace an item's labels with exactly `label_ids` (or "unlabeled" when empty)."""
    await _ensure_item_exists(session, item_id)
    unique_ids = set(label_ids)
    await _get_assignable_labels(session, unique_ids)

    await session.execute(delete(ItemLabel).where(ItemLabel.item_id == item_id))
    if unique_ids:
        await session.execute(
            insert(ItemLabel),
            [
                {"item_id": item_id, "label_id": label_id, "assigned_by": assigned_by}
                for label_id in unique_ids
            ],
        )
    await ensure_labeled(session, [item_id])
    await session.commit()
