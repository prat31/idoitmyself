import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.item import ItemRead
from app.services import items as item_service

router = APIRouter()


@router.get("", response_model=Page[ItemRead])
async def list_items(
    source_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[ItemRead]:
    items, total = await item_service.list_items(
        db, source_id=source_id, limit=limit, offset=offset
    )
    return Page(
        items=[ItemRead.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ItemRead:
    return ItemRead.model_validate(await item_service.get_item(db, item_id))
