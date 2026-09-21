"""ThathaCash Home screen and suggested order."""

from __future__ import annotations

from tests.conftest import Api


def test_a_new_account_has_an_empty_home_and_nothing_to_order(api: Api) -> None:
    status, body = api.get("/home")
    assert status == 200
    data = body["data"]
    assert data["cash"]["cashAvailable"] == 0
    assert data["cash"]["hasEntries"] is False
    assert data["order"] == {"total": 0, "itemCount": 0, "withinBudget": True}
    assert data["stock"] == {"items": [], "lowCount": 0, "totalCount": 0}
    assert data["recentEntries"] == []

    status, body = api.get("/order")
    assert status == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_suggests_only_running_low_products(api: Api) -> None:
    products = [
        # name, price, in stock, low at, usually order
        ("Coca-Cola 2L", 28, 5, 6, 12),  # low  -> 12 x 28 = 336
        ("Bread", 16, 3, 5, 20),  # low  -> 20 x 16 = 320
        ("Cooking Oil 750ml", 38.5, 0, 4, 6),  # out  -> 6 x 38.50 = 231
        ("Milk 1L", 18, 12, 6, 12),  # good -> not ordered
    ]
    for name, price, quantity, low, reorder in products:
        status, body = api.post(
            "/items",
            {
                "name": name,
                "price": price,
                "quantity": quantity,
                "lowStockLevel": low,
                "reorderQuantity": reorder,
            },
        )
        assert status == 201, body

    _, body = api.get("/order")
    order = body["data"]
    names = [line["name"] for line in order["items"]]
    # Emptiest shelves first.
    assert names == ["Cooking Oil 750ml", "Bread", "Coca-Cola 2L"]

    oil = order["items"][0]
    assert oil["inStock"] == 0
    assert oil["orderQuantity"] == 6
    assert oil["unitPrice"] == 38.5
    assert oil["lineTotal"] == 231

    assert order["total"] == 887


def test_an_order_with_no_cash_is_over_budget(api: Api) -> None:
    _, body = api.get("/order")
    assert body["data"]["availableForStock"] == 0
    assert body["data"]["withinBudget"] is False


def test_an_order_within_the_stock_budget(api: Api) -> None:
    # R2,000 cash -> R1,400 available for stock, which covers R887.
    api.post("/cash", {"type": "OPENING", "amount": 2000})
    _, body = api.get("/order")
    assert body["data"]["availableForStock"] == 1400
    assert body["data"]["withinBudget"] is True


def test_restocking_removes_a_product_from_the_order(api: Api) -> None:
    _, items = api.get("/items")
    bread = next(i for i in items["data"] if i["name"] == "Bread")
    api.patch(f"/items/{bread['id']}", {"quantity": 30})

    _, body = api.get("/order")
    assert "Bread" not in [line["name"] for line in body["data"]["items"]]
    assert body["data"]["total"] == 567


def test_home_brings_it_all_together(api: Api) -> None:
    api.post("/cash", {"type": "INCOME", "amount": 500, "note": "Customer sales"})

    _, body = api.get("/home")
    data = body["data"]

    assert data["cash"]["cashAvailable"] == 2500
    assert data["cash"]["availableForStock"] == 1750
    assert data["cash"]["keptForExpenses"] == 750

    assert data["order"] == {"total": 567, "itemCount": 2, "withinBudget": True}

    assert data["stock"]["totalCount"] == 4
    assert data["stock"]["lowCount"] == 2
    # Running-low products come first in the preview.
    statuses = [p["status"] for p in data["stock"]["items"]]
    assert statuses == ["LOW", "LOW", "GOOD", "GOOD"]

    assert [e["type"] for e in data["recentEntries"]][0] in ("INCOME", "OPENING")
    assert len(data["recentEntries"]) == 2


def test_home_and_order_require_login(anon: Api) -> None:
    assert anon.get("/home")[0] == 401
    assert anon.get("/order")[0] == 401
