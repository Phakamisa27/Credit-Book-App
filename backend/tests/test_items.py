"""Quick-entry items."""

from __future__ import annotations

from tests.conftest import Api

STATE: dict[str, int] = {}


def test_creates_a_quick_item(api: Api) -> None:
    status, body = api.post("/items", {"name": "Bread", "price": 18.5})
    assert status == 201
    assert body["data"]["price"] == 18.5
    assert body["data"]["name"] == "Bread"
    STATE["item_id"] = body["data"]["id"]


def test_refuses_a_duplicate_name(api: Api) -> None:
    status, body = api.post("/items", {"name": "Bread", "price": 20})
    assert status == 409
    assert "quick item" in body["message"]


def test_rejects_a_zero_price(api: Api) -> None:
    status, _ = api.post("/items", {"name": "Free thing", "price": 0})
    assert status == 400


def test_rejects_a_blank_name(api: Api) -> None:
    status, _ = api.post("/items", {"name": "  ", "price": 5})
    assert status == 400


def test_lists_items_alphabetically(api: Api) -> None:
    api.post("/items", {"name": "Airtime", "price": 30})
    _, body = api.get("/items")
    names = [i["name"] for i in body["data"]]
    assert names == sorted(names)


def test_deletes_an_item(api: Api) -> None:
    status, _ = api.delete(f"/items/{STATE['item_id']}")
    assert status == 200

    _, body = api.get("/items")
    assert not any(i["id"] == STATE["item_id"] for i in body["data"])


def test_deleting_an_unknown_item_404s(api: Api) -> None:
    assert api.delete("/items/99999999")[0] == 404
