import uuid
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRequestError
from app.models.label import AssignedBy
from app.services import labels as label_service

ItemFactory = Callable[..., Awaitable[uuid.UUID]]


async def label_ids(client: AsyncClient) -> dict[str, str]:
    return {label["slug"]: label["id"] for label in (await client.get("/api/v1/labels")).json()}


def slugs(item: dict) -> list[str]:
    return [label["slug"] for label in item["labels"]]


async def get_item(client: AsyncClient, item_id: uuid.UUID) -> dict:
    return (await client.get(f"/api/v1/items/{item_id}")).json()


async def test_new_items_are_unlabeled(client: AsyncClient, item_factory: ItemFactory) -> None:
    item = await get_item(client, await item_factory())

    assert slugs(item) == ["unlabeled"]
    assert item["labels"][0]["assigned_by"] == "system"


async def test_adding_a_label_replaces_unlabeled(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)

    response = await client.post(f"/api/v1/items/{item_id}/labels", json={"label_id": ids["work"]})
    assert response.status_code == 200
    assert slugs(response.json()) == ["work"]
    assert response.json()["labels"][0]["assigned_by"] == "manual"

    response = await client.post(
        f"/api/v1/items/{item_id}/labels", json={"label_id": ids["finance"]}
    )
    assert slugs(response.json()) == ["finance", "work"]


async def test_adding_same_label_twice_is_idempotent(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)

    for _ in range(2):
        response = await client.post(
            f"/api/v1/items/{item_id}/labels", json={"label_id": ids["work"]}
        )
    assert slugs(response.json()) == ["work"]


async def test_removing_last_label_falls_back_to_unlabeled(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)
    await client.post(f"/api/v1/items/{item_id}/labels", json={"label_id": ids["work"]})

    response = await client.delete(f"/api/v1/items/{item_id}/labels/{ids['work']}")
    assert response.status_code == 200
    assert slugs(response.json()) == ["unlabeled"]


async def test_removing_a_label_the_item_does_not_have(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)

    response = await client.delete(f"/api/v1/items/{item_id}/labels/{ids['work']}")
    assert response.status_code == 404


async def test_unlabeled_cannot_be_assigned_or_removed_manually(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)

    response = await client.post(
        f"/api/v1/items/{item_id}/labels", json={"label_id": ids["unlabeled"]}
    )
    assert response.status_code == 422
    response = await client.delete(f"/api/v1/items/{item_id}/labels/{ids['unlabeled']}")
    assert response.status_code == 422
    response = await client.put(
        f"/api/v1/items/{item_id}/labels", json={"label_ids": [ids["unlabeled"]]}
    )
    assert response.status_code == 422


async def test_set_labels_replaces_all(client: AsyncClient, item_factory: ItemFactory) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)
    custom = (await client.post("/api/v1/labels", json={"name": "Taxes"})).json()

    response = await client.put(
        f"/api/v1/items/{item_id}/labels",
        json={"label_ids": [ids["finance"], custom["id"], ids["finance"]]},
    )
    assert response.status_code == 200
    assert slugs(response.json()) == ["finance", "taxes"]

    response = await client.put(f"/api/v1/items/{item_id}/labels", json={"label_ids": []})
    assert slugs(response.json()) == ["unlabeled"]


async def test_set_labels_with_unknown_label_changes_nothing(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)
    await client.put(f"/api/v1/items/{item_id}/labels", json={"label_ids": [ids["work"]]})

    response = await client.put(
        f"/api/v1/items/{item_id}/labels", json={"label_ids": [ids["finance"], str(uuid.uuid4())]}
    )
    assert response.status_code == 404
    assert slugs(await get_item(client, item_id)) == ["work"]


async def test_labelling_unknown_item_returns_404(client: AsyncClient) -> None:
    ids = await label_ids(client)
    response = await client.post(
        f"/api/v1/items/{uuid.uuid4()}/labels", json={"label_id": ids["work"]}
    )
    assert response.status_code == 404


async def test_deleting_custom_label_relabels_orphaned_items(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    only_custom, custom_and_work = await item_factory(), await item_factory()
    ids = await label_ids(client)
    custom = (await client.post("/api/v1/labels", json={"name": "Temp"})).json()
    await client.put(f"/api/v1/items/{only_custom}/labels", json={"label_ids": [custom["id"]]})
    await client.put(
        f"/api/v1/items/{custom_and_work}/labels", json={"label_ids": [custom["id"], ids["work"]]}
    )

    await client.delete(f"/api/v1/labels/{custom['id']}")

    assert slugs(await get_item(client, only_custom)) == ["unlabeled"]
    assert slugs(await get_item(client, custom_and_work)) == ["work"]


async def test_filter_items_by_label_and_counts(
    client: AsyncClient, item_factory: ItemFactory
) -> None:
    work_item = await item_factory(title="Standup")
    await item_factory(title="Lunch?")
    ids = await label_ids(client)
    await client.post(f"/api/v1/items/{work_item}/labels", json={"label_id": ids["work"]})

    page = (await client.get("/api/v1/items", params={"label": "work"})).json()
    assert [i["title"] for i in page["items"]] == ["Standup"]
    page = (await client.get("/api/v1/items", params={"label": "unlabeled"})).json()
    assert [i["title"] for i in page["items"]] == ["Lunch?"]

    counts = {
        label["slug"]: label["item_count"] for label in (await client.get("/api/v1/labels")).json()
    }
    assert counts["work"] == 1
    assert counts["unlabeled"] == 1
    label = (await client.get(f"/api/v1/labels/{ids['work']}")).json()
    assert label["item_count"] == 1


async def test_ai_assignment_records_provenance(
    db: AsyncSession, client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)

    await label_service.add_item_label(
        db, item_id, uuid.UUID(ids["promotions"]), assigned_by=AssignedBy.AI, confidence=0.87
    )

    (label,) = (await get_item(client, item_id))["labels"]
    assert (label["slug"], label["assigned_by"], label["confidence"]) == ("promotions", "ai", 0.87)

    # A later manual assignment of the same label overrides the AI one.
    response = await client.post(
        f"/api/v1/items/{item_id}/labels", json={"label_id": ids["promotions"]}
    )
    (label,) = response.json()["labels"]
    assert (label["assigned_by"], label["confidence"]) == ("manual", None)


async def test_resync_keeps_existing_labels(
    db: AsyncSession, client: AsyncClient, item_factory: ItemFactory
) -> None:
    item_id = await item_factory(external_id="m1")
    ids = await label_ids(client)
    await client.post(f"/api/v1/items/{item_id}/labels", json={"label_id": ids["work"]})

    # Same external id from the same source: an update, not a new item.
    assert await item_factory(title="Edited", external_id="m1") == item_id

    item = await get_item(client, item_id)
    assert item["title"] == "Edited"
    assert slugs(item) == ["work"]


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
async def test_confidence_must_be_between_0_and_1(
    db: AsyncSession, client: AsyncClient, item_factory: ItemFactory, confidence: float
) -> None:
    item_id = await item_factory()
    ids = await label_ids(client)
    with pytest.raises(InvalidRequestError):
        await label_service.add_item_label(
            db, item_id, uuid.UUID(ids["work"]), assigned_by=AssignedBy.AI, confidence=confidence
        )
