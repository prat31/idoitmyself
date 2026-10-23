from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


async def get_or_create_tags(session: AsyncSession, names: list[str]) -> list[Tag]:
    """Return Tag rows for `names` (matched case-insensitively), creating any that don't exist."""
    if not names:
        return []
    # Existing names (in any letter case) hit the unique lower(name) index and are skipped.
    await session.execute(insert(Tag).values([{"name": name} for name in names]).on_conflict_do_nothing())
    lowered = [name.lower() for name in names]
    result = await session.scalars(select(Tag).where(func.lower(Tag.name).in_(lowered)))
    return list(result)


async def list_tags(session: AsyncSession) -> list[Tag]:
    result = await session.scalars(select(Tag).order_by(func.lower(Tag.name)))
    return list(result)
