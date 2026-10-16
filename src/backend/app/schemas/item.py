import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    external_id: str
    kind: str
    title: str | None
    author: str | None
    content: str | None
    occurred_at: datetime | None
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
