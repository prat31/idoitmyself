from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from app.models.source import Source, SourceType


@dataclass(frozen=True)
class FetchedItem:
    """Source-agnostic representation of one item, as produced by a connector."""

    external_id: str
    kind: str
    title: str | None = None
    author: str | None = None
    content: str | None = None
    occurred_at: datetime | None = None
    data: dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    """Fetches items from one external system.

    Connectors only translate the provider's data into `FetchedItem`s; persistence,
    deduplication and labelling are handled by the ingestion service so every source
    behaves the same way once its data is in the database.
    """

    source_type: ClassVar[SourceType]

    def __init__(self, source: Source) -> None:
        self.source = source

    @abstractmethod
    def fetch_items(self, since: datetime | None) -> AsyncIterator[FetchedItem]:
        """Yield items created or changed after `since` (all items when None)."""
