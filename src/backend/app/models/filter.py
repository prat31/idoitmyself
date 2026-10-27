import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.inbox import Inbox, InboxProvider, provider_enum
from app.models.label import Label


class FilterStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# Individually chosen inboxes a filter applies to (see Filter's scope).
filter_inboxes = Table(
    "filter_inboxes",
    Base.metadata,
    Column("filter_id", UUID(as_uuid=True), ForeignKey("filters.id", ondelete="CASCADE"), primary_key=True),
    Column("inbox_id", UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), primary_key=True),
)


class FilterMailboxType(Base):
    """A whole mailbox type a filter applies to: every inbox of that type, including ones connected
    later."""

    __tablename__ = "filter_mailbox_types"

    filter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filters.id", ondelete="CASCADE"), primary_key=True
    )
    mailbox_type: Mapped[InboxProvider] = mapped_column(provider_enum, primary_key=True)


class Filter(TimestampMixin, Base):
    """A rule over an email's fields (see app.filters). When an email scanned while the filter is
    active passes it, the filter's label is added. Filters only ever add labels.

    Scope: the filter applies to every inbox of its `mailbox_types` plus the `inboxes` chosen one by
    one (types may be mixed). Its rule may only use fields available to every type it covers."""

    __tablename__ = "filters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    # RESTRICT: a label can't be deleted while a filter writes to it.
    label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("labels.id", ondelete="RESTRICT"), index=True
    )
    # Validated by app.schemas.filter.Rule; stored as its JSON form.
    rule: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[FilterStatus] = mapped_column(
        Enum(FilterStatus, name="filter_status", values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set on built-in defaults (see app.defaults): they can be edited and deactivated, but not deleted.
    default_key: Mapped[str | None] = mapped_column(String(100), unique=True)

    label: Mapped[Label] = relationship(lazy="joined")
    mailbox_types: Mapped[list[FilterMailboxType]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by=FilterMailboxType.mailbox_type
    )
    inboxes: Mapped[list[Inbox]] = relationship(
        secondary=filter_inboxes, lazy="selectin", order_by=Inbox.name
    )

    def covers(self, inbox: Inbox) -> bool:
        return any(t.mailbox_type == inbox.provider for t in self.mailbox_types) or any(
            i.id == inbox.id for i in self.inboxes
        )
