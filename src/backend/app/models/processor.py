import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.label import Label


class ProcessorStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProcessorRunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"  # nothing to do (e.g. no parser for the sender, no PDF); not a failure
    FAILED = "failed"
    # Waiting for something only the user can give (e.g. a PDF password). Saving it queues the run again.
    NEEDS_INPUT = "needs_input"
    CANCELLED = "cancelled"  # its processor was deleted before it ran


ACTIVE_RUN_STATUSES = (ProcessorRunStatus.QUEUED, ProcessorRunStatus.RUNNING)


class ActionStatus(enum.StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _pg_enum(enum_cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


# The labels that trigger a processor (n–n). RESTRICT: a label can't be deleted while a processor uses it.
processor_labels = Table(
    "processor_labels",
    Base.metadata,
    Column(
        "processor_id", UUID(as_uuid=True), ForeignKey("processors.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("label_id", UUID(as_uuid=True), ForeignKey("labels.id", ondelete="RESTRICT"), primary_key=True),
)


class Processor(TimestampMixin, Base):
    """An instance of a processor kind (app.processors: code). It runs on every email that newly gets
    any of its labels, while active. The kind is fixed once created; the labels can change."""

    __tablename__ = "processors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(50))
    # Validated by the kind's `config` model ({} for kinds without one).
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    status: Mapped[ProcessorStatus] = mapped_column(_pg_enum(ProcessorStatus, "processor_status"), index=True)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set on built-in defaults (see app.defaults): they can be edited and deactivated, but not deleted.
    default_key: Mapped[str | None] = mapped_column(String(100), unique=True)

    labels: Mapped[list[Label]] = relationship(
        secondary=processor_labels, lazy="selectin", order_by=Label.display_name
    )


class ProcessorRun(TimestampMixin, Base):
    """One processor on one email: at most one per pair (a re-run reuses it). Created when the email
    gets one of the processor's labels (in the same transaction), or on request. Kept after the
    processor is deleted."""

    __tablename__ = "processor_runs"
    __table_args__ = (UniqueConstraint("processor_id", "email_id", name="uq_processor_runs_processor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processors.id", ondelete="SET NULL"), index=True
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), index=True
    )
    # The processor's labels the email carried when the run was queued (the ones that triggered it).
    trigger_label_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default=text("'{}'")
    )
    status: Mapped[ProcessorRunStatus] = mapped_column(
        _pg_enum(ProcessorRunStatus, "processor_run_status"), index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    kind_version: Mapped[int | None] = mapped_column(Integer)  # of the kind's code that last ran it
    records_written: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # What a `needs_input` run waits for: an input name and scope (see InputValue), and what to ask.
    input_name: Mapped[str | None] = mapped_column(String(50))
    input_scope: Mapped[str | None] = mapped_column(Text)
    input_prompt: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Record(Base):
    """One row of a dataset (app.processors.records), written by a processor for an email. A re-run
    replaces the processor's records for that email. Kept after the processor is deleted."""

    __tablename__ = "records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[int] = mapped_column(Integer)
    processor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processors.id", ondelete="SET NULL")
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processor_runs.id", ondelete="SET NULL")
    )
    # Snapshot datasets: the identity of the thing described (the latest record per key wins).
    key: Mapped[str | None] = mapped_column(Text)
    # The dataset's time field, promoted for bucketing and ranges.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InputValue(TimestampMixin, Base):
    """Something a processor asked the user for (e.g. a PDF password), by name and scope (e.g. the
    sender and label). Fernet-encrypted; never returned by the API."""

    __tablename__ = "input_values"
    __table_args__ = (UniqueConstraint("name", "scope", name="uq_input_values_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    scope: Mapped[str] = mapped_column(Text)
    encrypted_value: Mapped[str] = mapped_column(Text)


class Action(TimestampMixin, Base):
    """A side effect a processor asked for (app.processors.actions), delivered once when due. Unique per
    processor, email and key, so a re-run never sends it twice (a pending one is updated instead)."""

    __tablename__ = "actions"
    __table_args__ = (UniqueConstraint("processor_id", "email_id", "key", name="uq_actions_processor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processors.id", ondelete="SET NULL"), index=True
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processor_runs.id", ondelete="SET NULL")
    )
    key: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ActionStatus] = mapped_column(_pg_enum(ActionStatus, "action_status"), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    # Last handed to the actions task; the tick re-publishes one stuck for long.
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    """An in-app notification: from a Notify action (also sent to Telegram when it's configured), or
    about a processor run that failed (in-app only). Dismissed ones leave the list."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The action it came from: unique, so a retried delivery never creates it twice.
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actions.id", ondelete="SET NULL"), unique=True
    )
    processor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processors.id", ondelete="SET NULL")
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    telegram_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
