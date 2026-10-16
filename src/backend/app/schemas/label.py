import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from app.models.label import Label, LabelKind

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    description: str | None = Field(default=None, max_length=500)


class LabelUpdate(BaseModel):
    """Partial update; omitted fields are left unchanged, `null` clears color/description."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    description: str | None = Field(default=None, max_length=500)


class LabelRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    kind: LabelKind
    color: str | None
    description: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_label(cls, label: Label, item_count: int) -> Self:
        return cls(
            id=label.id,
            name=label.name,
            slug=label.slug,
            kind=label.kind,
            color=label.color,
            description=label.description,
            item_count=item_count,
            created_at=label.created_at,
            updated_at=label.updated_at,
        )
