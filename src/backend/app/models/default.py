from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppliedDefault(Base):
    """A built-in default (app.defaults) that has been seeded. Each is seeded once: one the user
    changes keeps their changes, and one they made redundant (e.g. by naming a label the same) isn't
    added again."""

    __tablename__ = "applied_defaults"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
