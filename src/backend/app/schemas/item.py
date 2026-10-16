import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel

from app.models.item import Item
from app.models.label import AssignedBy, ItemLabel, LabelKind


class ItemLabelRead(BaseModel):
    """A label as attached to a specific item."""

    id: uuid.UUID
    name: str
    slug: str
    kind: LabelKind
    color: str | None
    assigned_by: AssignedBy
    confidence: float | None
    assigned_at: datetime

    @classmethod
    def from_link(cls, link: ItemLabel) -> Self:
        return cls(
            id=link.label.id,
            name=link.label.name,
            slug=link.label.slug,
            kind=link.label.kind,
            color=link.label.color,
            assigned_by=link.assigned_by,
            confidence=link.confidence,
            assigned_at=link.assigned_at,
        )


class ItemRead(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    external_id: str
    kind: str
    title: str | None
    author: str | None
    content: str | None
    occurred_at: datetime | None
    data: dict[str, Any]
    labels: list[ItemLabelRead]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_item(cls, item: Item) -> Self:
        """Build from an Item whose `label_links` (and their labels) are loaded."""
        links = sorted(item.label_links, key=lambda link: link.label.name.lower())
        return cls.model_validate(
            {
                **{name: getattr(item, name) for name in cls.model_fields if name != "labels"},
                "labels": [ItemLabelRead.from_link(link) for link in links],
            }
        )


class ItemLabelsSet(BaseModel):
    """Replace all labels on an item. An empty list leaves it "unlabeled"."""

    label_ids: list[uuid.UUID]


class ItemLabelAdd(BaseModel):
    label_id: uuid.UUID
