import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tag import Tag, inbox_tags


class InboxProvider(enum.StrEnum):
    GMAIL = "gmail"


class Inbox(TimestampMixin, Base):
    """A connected email account."""

    __tablename__ = "inboxes"
    __table_args__ = (
        UniqueConstraint("provider", "email_address", name="uq_inboxes_provider_email_address"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[InboxProvider] = mapped_column(
        Enum(InboxProvider, name="inbox_provider", values_callable=lambda e: [m.value for m in e])
    )
    name: Mapped[str] = mapped_column(String(100))
    email_address: Mapped[str] = mapped_column(String(320))
    notes: Mapped[str | None] = mapped_column(Text)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    tags: Mapped[list[Tag]] = relationship(secondary=inbox_tags, lazy="selectin", order_by=Tag.name)
    credential: Mapped["InboxCredential"] = relationship(
        back_populates="inbox", cascade="all, delete-orphan", uselist=False
    )


class InboxCredential(TimestampMixin, Base):
    """OAuth credentials for an inbox. Tokens are Fernet-encrypted; kept apart from `inboxes` on purpose."""

    __tablename__ = "inbox_credentials"

    inbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    access_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text))

    inbox: Mapped[Inbox] = relationship(back_populates="credential")
