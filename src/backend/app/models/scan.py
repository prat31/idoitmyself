import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.filter import Filter


class ScanKind(enum.StrEnum):
    SCHEDULED = "scheduled"  # Celery beat, every interval: from the inbox's last scheduled scan to now
    ADHOC = "adhoc"  # requested by the user: chosen filters over a past date range


class ScanStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"  # stopped by the user; work already done (stored emails, labels) stays


ACTIVE_SCAN_STATUSES = (ScanStatus.QUEUED, ScanStatus.RUNNING)


def _pg_enum(enum_cls: type[enum.StrEnum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


# The filters an ad hoc scan runs (periodic scans use every active filter covering the inbox).
scan_filters = Table(
    "scan_filters",
    Base.metadata,
    Column("scan_id", UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True),
    Column("filter_id", UUID(as_uuid=True), ForeignKey("filters.id", ondelete="CASCADE"), primary_key=True),
)


class Scan(TimestampMixin, Base):
    """One scan of one inbox: list emails received in a time window, run the ones no scan has stored yet
    through filters, add labels. Scheduled scans are started by the tick (Celery beat) and use every
    active filter covering the inbox; ad hoc scans are requested by the user for chosen filters and a
    past date range."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[ScanKind] = mapped_column(_pg_enum(ScanKind, "scan_kind"))
    status: Mapped[ScanStatus] = mapped_column(_pg_enum(ScanStatus, "scan_status"), index=True)
    # Emails received in [window_start, window_end) are listed. Scheduled scans' windows join up: each
    # starts where the inbox's previous one ended.
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set once the inbox has been listed and the batches published.
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    # Stats, updated as the scan progresses.
    emails_found: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_processed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Of emails_processed: already stored by an earlier scan, so not fetched or filtered again.
    emails_skipped: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_failed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    emails_matched: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    labels_applied: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # Emails re-queued with a delay after a provider error (one email can be retried several times).
    retries: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    # Ad hoc scans only.
    filters: Mapped[list["Filter"]] = relationship(
        secondary=scan_filters, lazy="selectin", order_by="Filter.name"
    )


class InboxSync(TimestampMixin, Base):
    """Where an inbox's next scheduled scan starts. No row means it has never been scanned on schedule."""

    __tablename__ = "inbox_sync"

    inbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), primary_key=True
    )
    # End of the last scheduled scan's window, set once that window was listed.
    scanned_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
