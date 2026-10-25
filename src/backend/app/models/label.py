import uuid

from sqlalchemy import CheckConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

# Fixed colour palette (keys only; the frontend owns the actual colours, light and dark).
LABEL_COLORS = ("gray", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink")


class Label(TimestampMixin, Base):
    """An IDIM label: just a name. Global (shared by all inboxes) and provider-agnostic — not a
    provider's own label. Filters add labels to emails.

    `name` is the normalised form (see schemas.label.normalize_label_name): unique and immutable.
    `display_name` is what the UI shows, and can be edited; so can `color`, from LABEL_COLORS."""

    __tablename__ = "labels"
    __table_args__ = (
        UniqueConstraint("name", name="uq_labels_name"),
        CheckConstraint(
            "name <> '' AND name = btrim(regexp_replace(lower(name), '[^[:alnum:]]+', '_', 'g'), '_')",
            name="name_normalized",
        ),
        CheckConstraint(f"color IN ({', '.join(repr(c) for c in LABEL_COLORS)})", name="color_in_palette"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    display_name: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(20), default="gray", server_default=text("'gray'"))
