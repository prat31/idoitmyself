from collections.abc import AsyncIterator
from datetime import datetime
from typing import ClassVar

from app.models.source import SourceType
from app.sources.base import FetchedItem, SourceConnector


class FakeConnector(SourceConnector):
    """In-memory connector; tests set `items` before syncing."""

    source_type: ClassVar[SourceType] = SourceType.GMAIL
    items: ClassVar[list[FetchedItem]] = []
    seen_since: ClassVar[list[datetime | None]] = []

    async def fetch_items(self, since: datetime | None) -> AsyncIterator[FetchedItem]:
        self.seen_since.append(since)
        for item in self.items:
            yield item
