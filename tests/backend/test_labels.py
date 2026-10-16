import uuid

from httpx import AsyncClient

SYSTEM_SLUGS = {
    "unlabeled",
    "important",
    "personal",
    "work",
    "finance",
    "travel",
    "shopping",
    "social",
    "promotions",
    "updates",
    "newsletters",
}


async def create_label(client: AsyncClient, name: str, **fields: str) -> dict:
    response = await client.post("/api/v1/labels", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


async def test_predefined_labels_are_seeded(client: AsyncClient) -> None:
    labels = (await client.get("/api/v1/labels")).json()

    assert {label["slug"] for label in labels} == SYSTEM_SLUGS
    assert all(label["kind"] == "system" for label in labels)
    assert all(label["item_count"] == 0 for label in labels)


async def test_create_custom_label(client: AsyncClient) -> None:
    label = await create_label(client, "  Side Projects ", color="#112233", description="Hobby")

    assert label["name"] == "Side Projects"
    assert label["slug"] == "side-projects"
    assert label["kind"] == "custom"
    assert label["color"] == "#112233"
    assert label["item_count"] == 0


async def test_custom_labels_listed_after_system_labels(client: AsyncClient) -> None:
    await create_label(client, "Aaa")

    labels = (await client.get("/api/v1/labels")).json()
    assert labels[-1]["name"] == "Aaa"
    custom = (await client.get("/api/v1/labels", params={"kind": "custom"})).json()
    assert [label["name"] for label in custom] == ["Aaa"]


async def test_label_names_are_unique_case_insensitively(client: AsyncClient) -> None:
    await create_label(client, "Side Projects")

    response = await client.post("/api/v1/labels", json={"name": "side  projects!"})
    assert response.status_code == 409
    # Custom labels cannot shadow predefined ones either.
    assert (await client.post("/api/v1/labels", json={"name": "WORK"})).status_code == 409


async def test_create_label_validates_input(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/labels", json={"name": "!!!"})).status_code == 422
    assert (await client.post("/api/v1/labels", json={"name": ""})).status_code == 422
    response = await client.post("/api/v1/labels", json={"name": "x", "color": "red"})
    assert response.status_code == 422


async def test_update_custom_label(client: AsyncClient) -> None:
    label = await create_label(client, "Receipts", color="#000000", description="old")

    response = await client.patch(
        f"/api/v1/labels/{label['id']}", json={"name": "Tax Receipts", "description": None}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["slug"] == "tax-receipts"
    assert updated["description"] is None
    assert updated["color"] == "#000000"  # omitted fields stay unchanged


async def test_rename_to_existing_name_conflicts(client: AsyncClient) -> None:
    await create_label(client, "One")
    two = await create_label(client, "Two")

    response = await client.patch(f"/api/v1/labels/{two['id']}", json={"name": "one"})
    assert response.status_code == 409
    # Renaming to its own name (different case) is fine.
    response = await client.patch(f"/api/v1/labels/{two['id']}", json={"name": "TWO"})
    assert response.status_code == 200


async def test_system_labels_are_read_only(client: AsyncClient) -> None:
    labels = (await client.get("/api/v1/labels", params={"kind": "system"})).json()
    work = next(label for label in labels if label["slug"] == "work")

    response = await client.patch(f"/api/v1/labels/{work['id']}", json={"color": "#ffffff"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert (await client.delete(f"/api/v1/labels/{work['id']}")).status_code == 403


async def test_get_and_delete_label(client: AsyncClient) -> None:
    label = await create_label(client, "Temp")

    assert (await client.get(f"/api/v1/labels/{label['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/labels/{label['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/labels/{label['id']}")).status_code == 404


async def test_unknown_label_returns_404(client: AsyncClient) -> None:
    response = await client.patch(f"/api/v1/labels/{uuid.uuid4()}", json={"name": "x"})
    assert response.status_code == 404
