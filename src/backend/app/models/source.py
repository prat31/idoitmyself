import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, str_enum


class SourceType(enum.StrEnum):
    """Kinds of external data sources. Each one needs a connector in app/sources/."""

    GMAIL = "gmail"


class Source(TimestampMixin, Base):
    """A configured external data source, e.g. one Gmail account."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[SourceType] = mapped_column(str_enum(SourceType))
    name: Mapped[str] = mapped_column(String(200))
    # Connector-specific, non-secret settings (e.g. which mailbox query to sync).
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
