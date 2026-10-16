import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.source import Source
from app.schemas.source import SourceCreate


async def list_sources(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[Source], int]:
    total = await session.scalar(select(func.count()).select_from(Source)) or 0
    result = await session.scalars(
        select(Source).order_by(Source.created_at, Source.id).limit(limit).offset(offset)
    )
    return list(result), total


async def get_source(session: AsyncSession, source_id: uuid.UUID) -> Source:
    source = await session.get(Source, source_id)
    if source is None:
        raise NotFoundError(f"Source {source_id} not found")
    return source


async def create_source(session: AsyncSession, data: SourceCreate) -> Source:
    source = Source(type=data.type, name=data.name, config=data.config)
    session.add(source)
    await session.commit()
    return source


async def delete_source(session: AsyncSession, source_id: uuid.UUID) -> None:
    """Delete a source together with all of its items."""
    source = await get_source(session, source_id)
    await session.delete(source)
    await session.commit()
