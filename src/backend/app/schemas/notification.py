import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: uuid.UUID
    title: str
    body: str | None
    created_at: datetime
    read_at: datetime | None
    processor_id: uuid.UUID | None
    processor_name: str | None
    # Opens the email it's about in the provider's web UI, if any.
    open_url: str | None


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    unread: int
    page: int
    page_size: int
