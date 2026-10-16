import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

# Tests run against a dedicated Postgres database; point the app at it before importing it.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/idim_test"
)

# Make `app` importable when running from the repo root (the API container sets PYTHONPATH).
BACKEND_DIR = Path(__file__).resolve().parents[2] / "src" / "backend"
if BACKEND_DIR.is_dir() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Reset the test database to an empty schema and apply all migrations."""
    config = Config(str(BACKEND_DIR / "alembic.ini") if BACKEND_DIR.is_dir() else "alembic.ini")
    config.attributes["configure_logger"] = False
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    """Remove rows created by a test, keeping data seeded by migrations."""
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE sources, items CASCADE"))


@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
