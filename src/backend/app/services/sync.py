from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.services.items import upsert_item
from app.sources.registry import get_connector


@dataclass(frozen=True)
class SyncResult:
    created: int
    updated: int


async def sync_source(session: AsyncSession, source: Source) -> SyncResult:
    """Pull new and changed items from a source into the database."""
    connector = get_connector(source)
    started_at = datetime.now(UTC)
    created = updated = 0

    async for fetched in connector.fetch_items(since=source.last_synced_at):
        _, is_new = await upsert_item(session, source, fetched)
        if is_new:
            created += 1
        else:
            updated += 1

    source.last_synced_at = started_at
    await session.commit()
    return SyncResult(created=created, updated=updated)
