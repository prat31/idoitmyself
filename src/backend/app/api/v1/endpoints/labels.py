import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.label import LabelKind
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate
from app.services import labels as label_service

router = APIRouter()


@router.get("", response_model=list[LabelRead])
async def list_labels(
    kind: LabelKind | None = None, db: AsyncSession = Depends(get_db)
) -> list[LabelRead]:
    rows = await label_service.list_labels(db, kind=kind)
    return [LabelRead.from_label(label, count) for label, count in rows]


@router.post("", response_model=LabelRead, status_code=status.HTTP_201_CREATED)
async def create_label(data: LabelCreate, db: AsyncSession = Depends(get_db)) -> LabelRead:
    label = await label_service.create_label(db, data)
    return LabelRead.from_label(label, item_count=0)


@router.get("/{label_id}", response_model=LabelRead)
async def get_label(label_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> LabelRead:
    label = await label_service.get_label(db, label_id)
    return LabelRead.from_label(label, await label_service.count_items(db, label.id))


@router.patch("/{label_id}", response_model=LabelRead)
async def update_label(
    label_id: uuid.UUID, data: LabelUpdate, db: AsyncSession = Depends(get_db)
) -> LabelRead:
    label = await label_service.update_label(db, label_id, data)
    return LabelRead.from_label(label, await label_service.count_items(db, label.id))


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(label_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await label_service.delete_label(db, label_id)
