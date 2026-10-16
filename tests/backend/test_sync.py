from datetime import UTC, datetime

import pytest
from fakes import FakeConnector
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRequestError
from app.models.source import Source, SourceType
from app.services.sync import sync_source
from app.sources import registry
from app.sources.base import FetchedItem


def email(external_id: str, title: str, day: int) -> FetchedItem:
    return FetchedItem(
        external_id=external_id,
        kind="email",
        title=title,
        author="alice@example.com",
        content="Hello",
        occurred_at=datetime(2026, 1, day, tzinfo=UTC),
        data={"thread_id": f"t-{external_id}"},
    )


@pytest.fixture
def fake_connector(monkeypatch: pytest.MonkeyPatch) -> type[FakeConnector]:
    monkeypatch.setitem(registry._connectors, SourceType.GMAIL, FakeConnector)
    monkeypatch.setattr(FakeConnector, "items", [])
    monkeypatch.setattr(FakeConnector, "seen_since", [])
    return FakeConnector


async def make_source(db: AsyncSession) -> Source:
    source = Source(type=SourceType.GMAIL, name="Test inbox")
    db.add(source)
    await db.commit()
    return source


async def test_sync_creates_items(
    db: AsyncSession, client: AsyncClient, fake_connector: type[FakeConnector]
) -> None:
    source = await make_source(db)
    fake_connector.items = [email("m1", "First", 1), email("m2", "Second", 2)]

    result = await sync_source(db, source)

    assert (result.created, result.updated) == (2, 0)
    assert source.last_synced_at is not None
    page = (await client.get("/api/v1/items", params={"source_id": str(source.id)})).json()
    assert page["total"] == 2
    # Newest first
    assert [i["title"] for i in page["items"]] == ["Second", "First"]
    assert page["items"][0]["data"] == {"thread_id": "t-m2"}


async def test_resync_updates_instead_of_duplicating(
    db: AsyncSession, client: AsyncClient, fake_connector: type[FakeConnector]
) -> None:
    source = await make_source(db)
    fake_connector.items = [email("m1", "First", 1)]
    await sync_source(db, source)
    first_sync_at = source.last_synced_at

    fake_connector.items = [email("m1", "First (edited)", 1), email("m2", "Second", 2)]
    result = await sync_source(db, source)

    assert (result.created, result.updated) == (1, 1)
    assert fake_connector.seen_since == [None, first_sync_at]
    page = (await client.get("/api/v1/items")).json()
    assert sorted(i["title"] for i in page["items"]) == ["First (edited)", "Second"]


async def test_same_external_id_in_different_sources_is_distinct(
    db: AsyncSession, client: AsyncClient, fake_connector: type[FakeConnector]
) -> None:
    fake_connector.items = [email("m1", "Hi", 1)]
    await sync_source(db, await make_source(db))
    await sync_source(db, await make_source(db))

    assert (await client.get("/api/v1/items")).json()["total"] == 2


async def test_sync_without_connector_fails(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "_connectors", {})
    source = await make_source(db)

    with pytest.raises(InvalidRequestError):
        await sync_source(db, source)


async def test_deleting_source_deletes_its_items(
    db: AsyncSession, client: AsyncClient, fake_connector: type[FakeConnector]
) -> None:
    source = await make_source(db)
    fake_connector.items = [email("m1", "Hi", 1)]
    await sync_source(db, source)
    item_id = (await client.get("/api/v1/items")).json()["items"][0]["id"]

    await client.delete(f"/api/v1/sources/{source.id}")

    assert (await client.get(f"/api/v1/items/{item_id}")).status_code == 404
