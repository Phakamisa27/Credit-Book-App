"""ThathaCash stock: counts, running-low status and updates on items."""

from __future__ import annotations

import pytest

from tests.conftest import TEST_PASSWORD, Api, delete_account, unique_email

STATE: dict[str, int] = {}


def test_creates_a_product_with_stock_fields(api: Api) -> None:
    status, body = api.post(
        "/items",
        {
            "name": "Coca-Cola 2L",
            "price": 28,
            "quantity": 5,
            "lowStockLevel": 6,
            "reorderQuantity": 12,
        },
    )
    assert status == 201
    item = body["data"]
    assert item["quantity"] == 5
    assert item["lowStockLevel"] == 6
    assert item["reorderQuantity"] == 12
    assert item["status"] == "LOW"
    STATE["cola"] = item["id"]


def test_the_old_credit_book_shape_still_works_with_defaults(api: Api) -> None:
    status, body = api.post("/items", {"name": "Airtime R30", "price": 30})
    assert status == 201
    item = body["data"]
    assert item["quantity"] == 0
    assert item["lowStockLevel"] == 5
    assert item["reorderQuantity"] == 10
    # 0 on the shelf is at or below 5, so it is running low.
    assert item["status"] == "LOW"


def test_a_well_stocked_product_is_good(api: Api) -> None:
    status, body = api.post(
        "/items", {"name": "Milk 1L", "price": 18, "quantity": 12, "lowStockLevel": 6}
    )
    assert status == 201
    assert body["data"]["status"] == "GOOD"
    STATE["milk"] = body["data"]["id"]


def test_running_low_includes_the_level_itself(api: Api) -> None:
    _, body = api.post(
        "/items", {"name": "Bread", "price": 16, "quantity": 5, "lowStockLevel": 5}
    )
    assert body["data"]["status"] == "LOW"


def test_updating_the_count_changes_the_status(api: Api) -> None:
    status, body = api.patch(f"/items/{STATE['cola']}", {"quantity": 24})
    assert status == 200
    assert body["data"]["quantity"] == 24
    assert body["data"]["status"] == "GOOD"
    # Fields not sent are left alone.
    assert body["data"]["price"] == 28
    assert body["data"]["reorderQuantity"] == 12


def test_updates_price_name_and_levels(api: Api) -> None:
    status, body = api.patch(
        f"/items/{STATE['milk']}",
        {"name": "Milk 1L Clover", "price": 19.5, "lowStockLevel": 15, "reorderQuantity": 6},
    )
    assert status == 200
    item = body["data"]
    assert item["name"] == "Milk 1L Clover"
    assert item["price"] == 19.5
    assert item["reorderQuantity"] == 6
    # 12 on the shelf is now at or below the new level of 15.
    assert item["status"] == "LOW"


def test_the_list_includes_stock_fields(api: Api) -> None:
    _, body = api.get("/items")
    cola = next(i for i in body["data"] if i["id"] == STATE["cola"])
    assert cola["quantity"] == 24
    assert cola["status"] == "GOOD"


@pytest.mark.parametrize(
    "patch, message",
    [
        ({"quantity": -1}, "Quantity must be at least 0."),
        ({"quantity": 2.5}, "Quantity must be a whole number."),
        ({"quantity": "lots"}, "Quantity must be a whole number."),
        ({"reorderQuantity": 0}, "Order quantity must be at least 1."),
        ({"lowStockLevel": -3}, "Running low level must be at least 0."),
        ({"price": 0}, "Price must be greater than zero."),
        ({"name": "   "}, "Item name is required."),
    ],
)
def test_rejects_invalid_updates(api: Api, patch: dict, message: str) -> None:
    status, body = api.patch(f"/items/{STATE['cola']}", patch)
    assert status == 400
    assert body["message"] == message


def test_rejects_a_negative_starting_quantity(api: Api) -> None:
    status, body = api.post("/items", {"name": "Sugar 2kg", "price": 42, "quantity": -4})
    assert status == 400
    assert body["message"] == "Quantity must be at least 0."


def test_updating_an_unknown_product_404s(api: Api) -> None:
    status, body = api.patch("/items/99999999", {"quantity": 1})
    assert status == 404
    assert body["message"] == "Product not found."


def test_another_account_cannot_update_our_stock(client, api: Api) -> None:
    email = unique_email("stock-other")
    status, body = Api(client).post(
        "/auth/register",
        {"fullName": "Other Owner", "email": email, "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 201
    other = Api(client, body["data"]["token"])
    try:
        assert other.patch(f"/items/{STATE['cola']}", {"quantity": 0})[0] == 404
        assert other.get("/items")[1]["data"] == []
    finally:
        delete_account(email)

    _, ours = api.get("/items")
    assert next(i for i in ours["data"] if i["id"] == STATE["cola"])["quantity"] == 24
