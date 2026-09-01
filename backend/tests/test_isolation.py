"""One account can never see or touch another account's books."""

from __future__ import annotations

import pytest

from tests.conftest import TEST_PASSWORD, Api, delete_account, unique_email


@pytest.fixture(scope="module")
def other(client, api: Api) -> Api:
    """A second owner, registered alongside the module's own owner."""
    email = unique_email("other")
    anonymous = Api(client)
    status, body = anonymous.post(
        "/auth/register",
        {"fullName": "Other Owner", "email": email, "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 201
    yield Api(client, body["data"]["token"])
    delete_account(email)


@pytest.fixture(scope="module")
def our_customer(api: Api, new_customer) -> int:
    customer_id = new_customer("Ours Alone")
    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 400, "description": "Goods", "dueDate": "2030-01-01"},
    )
    return customer_id


def test_the_other_account_starts_empty(other: Api, our_customer: int) -> None:
    _, body = other.get("/customers")
    assert body["data"] == []


def test_the_other_account_cannot_read_our_customer(other: Api, our_customer: int) -> None:
    assert other.get(f"/customers/{our_customer}")[0] == 404


def test_the_other_account_cannot_update_our_customer(other: Api, our_customer: int) -> None:
    assert other.patch(f"/customers/{our_customer}", {"fullName": "Hijacked"})[0] == 404


def test_the_other_account_cannot_delete_our_customer(other: Api, our_customer: int) -> None:
    assert other.delete(f"/customers/{our_customer}")[0] == 404


def test_the_other_account_cannot_post_to_our_customers_ledger(
    other: Api, our_customer: int
) -> None:
    status, _ = other.post(
        f"/customers/{our_customer}/transactions",
        {"type": "CREDIT", "amount": 100, "description": "Not yours", "dueDate": "2030-01-01"},
    )
    assert status == 404


def test_the_other_account_cannot_read_our_transactions(
    api: Api, other: Api, our_customer: int
) -> None:
    _, ours = api.get(f"/customers/{our_customer}/transactions")
    transaction_id = ours["data"]["transactions"][0]["id"]

    assert other.get(f"/transactions/{transaction_id}")[0] == 404
    assert other.delete(f"/transactions/{transaction_id}")[0] == 404


def test_the_other_accounts_reports_are_all_zero(other: Api, our_customer: int) -> None:
    _, body = other.get("/reports/summary")
    assert body["data"]["totalCustomers"] == 0
    assert body["data"]["totalOutstanding"] == 0
    assert body["data"]["totalCreditIssued"] == 0


def test_our_customer_survived_every_attempt(api: Api, our_customer: int) -> None:
    _, body = api.get(f"/customers/{our_customer}")
    assert body["data"]["fullName"] == "Ours Alone"
    assert body["data"]["balance"] == 400
