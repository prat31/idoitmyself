import uuid

from httpx import AsyncClient


async def test_create_and_get_source(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/sources",
        json={"type": "gmail", "name": "Personal", "config": {"query": "in:inbox"}},
    )
    assert response.status_code == 201
    source = response.json()
    assert source["type"] == "gmail"
    assert source["config"] == {"query": "in:inbox"}
    assert source["last_synced_at"] is None

    response = await client.get(f"/api/v1/sources/{source['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Personal"


async def test_list_sources_paginates(client: AsyncClient) -> None:
    for name in ("a", "b", "c"):
        await client.post("/api/v1/sources", json={"type": "gmail", "name": name})

    response = await client.get("/api/v1/sources", params={"limit": 2, "offset": 1})
    page = response.json()
    assert page["total"] == 3
    assert [s["name"] for s in page["items"]] == ["b", "c"]


async def test_create_source_rejects_unknown_type(client: AsyncClient) -> None:
    response = await client.post("/api/v1/sources", json={"type": "fax", "name": "x"})
    assert response.status_code == 422


async def test_delete_source(client: AsyncClient) -> None:
    source = (await client.post("/api/v1/sources", json={"type": "gmail", "name": "x"})).json()

    assert (await client.delete(f"/api/v1/sources/{source['id']}")).status_code == 204
    response = await client.get(f"/api/v1/sources/{source['id']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_unknown_source_returns_404(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/sources/{uuid.uuid4()}")
    assert response.status_code == 404
