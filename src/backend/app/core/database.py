import enum
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

# Deterministic constraint names so Alembic migrations stay stable across environments.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Adds created_at / updated_at columns maintained by the database."""

    # eager_defaults fetches server-generated values via RETURNING, so they can be
    # read after a flush without triggering a lazy load (not allowed under asyncio).
    __mapper_args__: Any = {"eager_defaults": True}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def str_enum(enum_cls: type[enum.Enum]) -> Enum:
    """Store a Python enum by value in a VARCHAR column (no native PG enum to migrate)."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
