import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.source import Source


class Item(TimestampMixin, Base):
    """A single piece of data pulled from a source (an email, for Gmail).

    Common fields are normalized into columns; anything source-specific
    (thread ids, recipients, provider flags) lives in `data`.
    """

    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Indexed through the (source_id, external_id) unique constraint.
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    # Identifier of the item in the source system, e.g. the Gmail message id.
    external_id: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    source: Mapped[Source] = relationship(lazy="raise")
