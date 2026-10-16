import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.source import SourceType


class SourceCreate(BaseModel):
    type: SourceType
    name: str = Field(min_length=1, max_length=200)
    config: dict[str, Any] = Field(default_factory=dict)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: SourceType
    name: str
    config: dict[str, Any]
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
