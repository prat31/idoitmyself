import hashlib
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def condition_hash(filter_condition: str) -> str:
    """Fingerprint of a label's filter condition, to know whether a stored evaluation is still current."""
    return hashlib.sha256(filter_condition.strip().encode()).hexdigest()


class Email(TimestampMixin, Base):
    """Provider-agnostic metadata for an email seen by a run. Bodies are never stored."""

    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("inbox_id", "provider_message_id", name="uq_emails_inbox_id_provider_message_id"),
        Index("ix_emails_inbox_id_sent_at", "inbox_id", "sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), index=True
    )
    # The provider's own ids (e.g. Gmail message / thread id), opaque to IDIM.
    provider_message_id: Mapped[str] = mapped_column(String(255))
    provider_thread_id: Mapped[str | None] = mapped_column(String(255))
    # RFC 5322 Message-ID header, stable across providers.
    internet_message_id: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    from_address: Mapped[str | None] = mapped_column(Text)
    to_addresses: Mapped[str | None] = mapped_column(Text)
    cc_addresses: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL")
    )


class EmailLabel(TimestampMixin, Base):
    """An IDIM label applied to an email, with the Jev probability and the run that set it."""

    __tablename__ = "email_labels"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    probability: Mapped[float] = mapped_column(Float)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL")
    )


class LabelEvaluation(Base):
    """Jev's answer for one (email, label) — yes or no — so later runs can skip pairs already asked.
    Tied to the filter condition it answered (`condition_hash`); editing the condition makes it stale."""

    __tablename__ = "label_evaluations"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    probability: Mapped[float] = mapped_column(Float)
    condition_hash: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL")
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
