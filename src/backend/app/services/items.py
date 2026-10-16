import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.item import Item
from app.models.source import Source
from app.sources.base import FetchedItem


async def list_items(
    session: AsyncSession,
    *,
    source_id: uuid.UUID | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Item], int]:
    query = select(Item)
    if source_id is not None:
        query = query.where(Item.source_id == source_id)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    result = await session.scalars(
        query.order_by(Item.occurred_at.desc().nulls_last(), Item.id).limit(limit).offset(offset)
    )
    return list(result), total


async def get_item(session: AsyncSession, item_id: uuid.UUID) -> Item:
    item = await session.get(Item, item_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} not found")
    return item


async def upsert_item(
    session: AsyncSession, source: Source, fetched: FetchedItem
) -> tuple[Item, bool]:
    """Insert or refresh an item identified by (source, external_id).

    Returns the item and whether it was newly created. Does not commit.
    """
    values = {
        "kind": fetched.kind,
        "title": fetched.title,
        "author": fetched.author,
        "content": fetched.content,
        "occurred_at": fetched.occurred_at,
        "data": fetched.data,
    }
    inserted_id = await session.scalar(
        insert(Item)
        .values(id=uuid.uuid4(), source_id=source.id, external_id=fetched.external_id, **values)
        .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
        .returning(Item.id)
    )
    item = await session.scalar(
        select(Item)
        .where(Item.source_id == source.id, Item.external_id == fetched.external_id)
        .execution_options(populate_existing=True)
    )
    assert item is not None
    if inserted_id is None:
        for key, value in values.items():
            setattr(item, key, value)
        await session.flush()
    return item, inserted_id is not None
