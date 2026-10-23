import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RunKind(enum.StrEnum):
    ADHOC = "adhoc"


class RunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _pg_enum(enum_cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Run(TimestampMixin, Base):
    """One classification run over a set of inboxes, labels and a time window."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[RunKind] = mapped_column(_pg_enum(RunKind, "run_kind"))
    status: Mapped[RunStatus] = mapped_column(_pg_enum(RunStatus, "run_status"), index=True)
    # Emails whose sent time falls in [window_start, window_end) are processed.
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model: Mapped[str] = mapped_column(String(255))
    # Re-ask the model about every email, even (email, label) pairs already evaluated.
    reclassify: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set once every inbox has been listed and the batches published.
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    # Stats, updated as the run progresses.
    emails_found: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_processed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Of emails_processed: handled with no Gmail fetch and no model call (everything already evaluated).
    emails_skipped: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_failed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_matched: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    labels_applied: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    labels_removed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Emails re-queued with a delay after a transient failure (one email can be retried several times).
    retries: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(16, 9), default=Decimal(0), server_default=text("0"))

    labels: Mapped[list["RunLabel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="selectin", order_by="RunLabel.label_name"
    )
    inboxes: Mapped[list["RunInbox"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="selectin", order_by="RunInbox.inbox_name"
    )


class RunLabel(Base):
    """A label as it was when the run was requested (snapshot), plus its per-run match count."""

    __tablename__ = "run_labels"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    label_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="SET NULL")
    )
    label_name: Mapped[str] = mapped_column(String(50))
    filter_condition: Mapped[str] = mapped_column(Text)
    match_threshold: Mapped[float] = mapped_column(Float)
    matched: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    run: Mapped[Run] = relationship(back_populates="labels")


class RunInbox(Base):
    """An inbox included in a run (snapshot of its name/address), plus its per-run email count."""

    __tablename__ = "run_inboxes"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    inbox_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="SET NULL")
    )
    inbox_name: Mapped[str] = mapped_column(String(100))
    email_address: Mapped[str] = mapped_column(String(320))
    emails_found: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)

    run: Mapped[Run] = relationship(back_populates="inboxes")
