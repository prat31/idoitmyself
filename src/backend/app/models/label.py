import uuid

from sqlalchemy import CheckConstraint, Float, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

# Fixed colour palette (keys only; the frontend owns the actual colours).
LABEL_COLORS = ("gray", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink")


class Label(TimestampMixin, Base):
    """An IDIM label. Global (shared by all inboxes) and provider-agnostic — not a provider's own label.
    `name` is stored normalized (see schemas.label.normalize_label_name) and is immutable."""

    __tablename__ = "labels"
    __table_args__ = (
        Index("uq_labels_name_lower", text("lower(name)"), unique=True),
        CheckConstraint(f"color IN ({', '.join(repr(c) for c in LABEL_COLORS)})", name="color_in_palette"),
        CheckConstraint(
            "name <> '' AND name = btrim(regexp_replace(lower(name), '[^[:alnum:]]+', '_', 'g'), '_')",
            name="name_normalized",
        ),
        CheckConstraint("match_threshold > 0 AND match_threshold < 1", name="match_threshold_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(20))
    # Plain-language rule for which emails belong under this label; becomes the classification
    # question put to the model. Optional.
    filter_condition: Mapped[str | None] = mapped_column(Text)
    # Jev's P(yes) must reach this for a run to apply the label.
    match_threshold: Mapped[float] = mapped_column(Float, default=0.5, server_default=text("0.5"))
