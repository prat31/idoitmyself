import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.models.item import Item

# Slug of the system label given to any item that has no other label.
UNLABELED_SLUG = "unlabeled"


class LabelKind(enum.StrEnum):
    SYSTEM = "system"  # predefined, seeded by migrations, read-only through the API
    CUSTOM = "custom"  # created by the user


class AssignedBy(enum.StrEnum):
    """Who attached a label to an item."""

    SYSTEM = "system"  # automatic, e.g. the "unlabeled" fallback
    MANUAL = "manual"  # the user, through the API/UI
    AI = "ai"  # an LLM classifier
    RULE = "rule"  # a user-defined rule


class Label(TimestampMixin, Base):
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    # Lowercase, URL-safe form of the name; unique, so names are unique case-insensitively.
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[LabelKind] = mapped_column(str_enum(LabelKind))
    color: Mapped[str | None] = mapped_column(String(7))
    description: Mapped[str | None] = mapped_column(Text)


class ItemLabel(Base):
    """Association between an item and one of its labels."""

    __tablename__ = "item_labels"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
    )
    __mapper_args__ = {"eager_defaults": True}

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    assigned_by: Mapped[AssignedBy] = mapped_column(str_enum(AssignedBy))
    # Classifier confidence in [0, 1] for AI assignments; NULL otherwise.
    confidence: Mapped[float | None] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    item: Mapped["Item"] = relationship(back_populates="label_links", lazy="raise")
    label: Mapped[Label] = relationship(lazy="raise")
