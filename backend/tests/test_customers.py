"""Customer create, read, update, delete and search."""

from __future__ import annotations

from tests.conftest import Api

STATE: dict[str, int] = {}


def test_rejects_a_customer_with_no_name(api: Api) -> None:
    status, body = api.post("/customers", {"fullName": "   ", "phone": "074 099 8882"})
    assert status == 400
    assert "Full name" in body["message"]


def test_rejects_an_invalid_phone_number(api: Api) -> None:
    status, body = api.post("/customers", {"fullName": "Bad Phone", "phone": "123"})
    assert status == 400
    assert "South African" in body["message"]


def test_rejects_an_invalid_gender(api: Api) -> None:
    status, body = api.post(
        "/customers", {"fullName": "Bad Gender", "phone": "074 099 8883", "gender": "other"}
    )
    assert status == 400
    assert "male or female" in body["message"]


def test_creates_a_customer_with_a_zero_balance(api: Api) -> None:
    status, body = api.post(
        "/customers",
        {
            "fullName": "Thando Mkhize",
            "phone": "074 099 8882",
            "address": "Umlazi",
            "gender": "female",
        },
    )
    assert status == 201
    assert body["data"]["fullName"] == "Thando Mkhize"
    assert body["data"]["balance"] == 0
    assert body["data"]["status"] == "PAID"
    assert body["data"]["transactionCount"] == 0
    STATE["customer_id"] = body["data"]["id"]


def test_refuses_a_duplicate_phone_number(api: Api) -> None:
    status, body = api.post("/customers", {"fullName": "Someone Else", "phone": "074 099 8882"})
    assert status == 409
    assert "phone number" in body["message"]


def test_finds_a_customer_by_name(api: Api) -> None:
    _, body = api.get("/customers?search=thando")
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == STATE["customer_id"]


def test_finds_a_customer_by_phone_typed_without_spaces(api: Api) -> None:
    _, body = api.get("/customers?search=0740998882")
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == STATE["customer_id"]


def test_returns_nothing_for_a_non_matching_search(api: Api) -> None:
    _, body = api.get("/customers?search=zzzzzz")
    assert body["data"] == []


def test_reads_one_customer_by_id(api: Api) -> None:
    status, body = api.get(f"/customers/{STATE['customer_id']}")
    assert status == 200
    assert body["data"]["fullName"] == "Thando Mkhize"
    assert body["data"]["address"] == "Umlazi"


def test_updates_only_the_fields_sent(api: Api) -> None:
    status, body = api.patch(f"/customers/{STATE['customer_id']}", {"address": "KwaMashu"})
    assert status == 200
    assert body["data"]["address"] == "KwaMashu"
    # Untouched fields survive a partial update.
    assert body["data"]["fullName"] == "Thando Mkhize"
    assert body["data"]["gender"] == "female"


def test_put_updates_the_same_way(api: Api) -> None:
    status, body = api.put(f"/customers/{STATE['customer_id']}", {"notes": "Pays on Fridays"})
    assert status == 200
    assert body["data"]["notes"] == "Pays on Fridays"
    assert body["data"]["fullName"] == "Thando Mkhize"


def test_rejects_an_invalid_phone_on_update(api: Api) -> None:
    status, _ = api.patch(f"/customers/{STATE['customer_id']}", {"phone": "12"})
    assert status == 400


def test_404s_for_a_customer_that_does_not_exist(api: Api) -> None:
    status, _ = api.get("/customers/99999999")
    assert status == 404


def test_rejects_a_non_numeric_id(api: Api) -> None:
    status, _ = api.get("/customers/abc")
    assert status == 400


def test_deletes_a_customer(api: Api, new_customer) -> None:
    customer_id = new_customer("Temporary Person")

    status, body = api.delete(f"/customers/{customer_id}")
    assert status == 200
    assert body["data"]["message"] == "Customer deleted."

    status, _ = api.get(f"/customers/{customer_id}")
    assert status == 404


def test_deleting_the_same_customer_twice_404s(api: Api, new_customer) -> None:
    customer_id = new_customer("Delete Twice")
    assert api.delete(f"/customers/{customer_id}")[0] == 200
    assert api.delete(f"/customers/{customer_id}")[0] == 404
