import uuid

from sqlalchemy import Column, ForeignKey, Index, String, Table, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

inbox_tags = Table(
    "inbox_tags",
    Base.metadata,
    Column("inbox_id", UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(TimestampMixin, Base):
    """A reusable tag. Names are unique case-insensitively."""

    __tablename__ = "tags"
    __table_args__ = (Index("uq_tags_name_lower", text("lower(name)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
