import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.item import ItemLabelAdd, ItemLabelsSet, ItemRead
from app.services import items as item_service
from app.services import labels as label_service

router = APIRouter()


@router.get("", response_model=Page[ItemRead])
async def list_items(
    source_id: uuid.UUID | None = None,
    label: str | None = Query(None, description="Only items with this label slug"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[ItemRead]:
    items, total = await item_service.list_items(
        db, source_id=source_id, label_slug=label, limit=limit, offset=offset
    )
    return Page(
        items=[ItemRead.from_item(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ItemRead:
    return ItemRead.from_item(await item_service.get_item(db, item_id))


@router.put("/{item_id}/labels", response_model=ItemRead)
async def set_item_labels(
    item_id: uuid.UUID, data: ItemLabelsSet, db: AsyncSession = Depends(get_db)
) -> ItemRead:
    """Replace all of the item's labels."""
    await label_service.set_item_labels(db, item_id, data.label_ids)
    return ItemRead.from_item(await item_service.get_item(db, item_id))


@router.post("/{item_id}/labels", response_model=ItemRead)
async def add_item_label(
    item_id: uuid.UUID, data: ItemLabelAdd, db: AsyncSession = Depends(get_db)
) -> ItemRead:
    await label_service.add_item_label(db, item_id, data.label_id)
    return ItemRead.from_item(await item_service.get_item(db, item_id))


@router.delete("/{item_id}/labels/{label_id}", response_model=ItemRead)
async def remove_item_label(
    item_id: uuid.UUID, label_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ItemRead:
    await label_service.remove_item_label(db, item_id, label_id)
    return ItemRead.from_item(await item_service.get_item(db, item_id))
