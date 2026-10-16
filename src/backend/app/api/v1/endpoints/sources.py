import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.source import SourceCreate, SourceRead
from app.services import sources as source_service

router = APIRouter()


@router.get("", response_model=Page[SourceRead])
async def list_sources(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[SourceRead]:
    sources, total = await source_service.list_sources(db, limit=limit, offset=offset)
    return Page(
        items=[SourceRead.model_validate(s) for s in sources],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(data: SourceCreate, db: AsyncSession = Depends(get_db)) -> SourceRead:
    source = await source_service.create_source(db, data)
    return SourceRead.model_validate(source)


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SourceRead:
    return SourceRead.model_validate(await source_service.get_source(db, source_id))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await source_service.delete_source(db, source_id)
