import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Email(TimestampMixin, Base):
    """Provider-agnostic metadata for an email seen by a scan, matched or not. Bodies are never stored."""

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
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL")
    )


class EmailLabel(Base):
    """An IDIM label on an email, with the filter and scan that added it. Never removed by filters."""

    __tablename__ = "email_labels"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    # The first filter that added it (several filters can write the same label).
    filter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filters.id", ondelete="SET NULL"), index=True
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL")
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
