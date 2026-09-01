"""Credit, payments and the derived balance.

Financial rules under test:
  * credit increases the outstanding balance
  * payment decreases it
  * a payment may never exceed the amount owed
  * money keeps its cents — no floating-point drift
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import Api


@pytest.fixture(scope="module")
def ledger_customer(new_customer) -> int:
    return new_customer("Ledger Test")


def test_rejects_an_amount_of_zero(api: Api, ledger_customer: int) -> None:
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "CREDIT", "amount": 0, "description": "Nothing", "dueDate": "2030-01-01"},
    )
    assert status == 400
    assert "greater than zero" in body["message"]


def test_rejects_a_negative_amount(api: Api, ledger_customer: int) -> None:
    status, _ = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "CREDIT", "amount": -100, "description": "Refund?", "dueDate": "2030-01-01"},
    )
    assert status == 400


def test_rejects_an_unknown_transaction_type(api: Api, ledger_customer: int) -> None:
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "REFUND", "amount": 100, "description": "Nope"},
    )
    assert status == 400
    assert "CREDIT, PAYMENT" in body["message"]


def test_rejects_a_credit_with_no_description(api: Api, ledger_customer: int) -> None:
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "CREDIT", "amount": 100, "dueDate": "2030-01-01"},
    )
    assert status == 400
    assert "Description" in body["message"]


def test_rejects_a_due_date_that_is_not_a_real_date(api: Api, ledger_customer: int) -> None:
    status, _ = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "CREDIT", "amount": 100, "description": "Bread", "dueDate": "2026-02-30"},
    )
    assert status == 400


def test_rejects_credit_against_a_customer_that_does_not_exist(api: Api) -> None:
    status, _ = api.post(
        "/customers/99999999/transactions",
        {"type": "CREDIT", "amount": 100, "description": "Bread", "dueDate": "2030-01-01"},
    )
    assert status == 404


def test_adds_up_credit_and_payments_to_the_right_balance(api: Api, ledger_customer: int) -> None:
    """The worked example: 500 + 300 + 200 credit, 400 + 100 paid, 500 left."""
    for amount in (500, 300, 200):
        status, _ = api.post(
            f"/customers/{ledger_customer}/transactions",
            {"type": "CREDIT", "amount": amount, "description": "Goods", "dueDate": "2030-01-01"},
        )
        assert status == 201

    for amount in (400, 100):
        status, _ = api.post(
            f"/customers/{ledger_customer}/transactions",
            {"type": "PAYMENT", "amount": amount, "description": "Cash payment"},
        )
        assert status == 201

    _, body = api.get(f"/customers/{ledger_customer}")
    assert body["data"]["totalCredit"] == 1000
    assert body["data"]["totalPaid"] == 500
    assert body["data"]["balance"] == 500
    assert body["data"]["status"] == "OWING"


def test_refuses_a_payment_larger_than_the_balance(api: Api, ledger_customer: int) -> None:
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "PAYMENT", "amount": 600, "description": "Overpay"},
    )
    assert status == 400
    assert "more than the balance" in body["message"]

    # And the balance is untouched.
    _, after = api.get(f"/customers/{ledger_customer}")
    assert after["data"]["balance"] == 500


def test_allows_a_payment_that_settles_the_balance_exactly(api: Api, ledger_customer: int) -> None:
    status, _ = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "PAYMENT", "amount": 500, "description": "Settled in full"},
    )
    assert status == 201

    _, body = api.get(f"/customers/{ledger_customer}")
    assert body["data"]["balance"] == 0
    assert body["data"]["status"] == "PAID"


def test_refuses_a_payment_when_nothing_is_owed(api: Api, ledger_customer: int) -> None:
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "PAYMENT", "amount": 10, "description": "Extra"},
    )
    assert status == 400
    assert "does not owe" in body["message"]


def test_refuses_a_due_date_on_a_payment(api: Api, ledger_customer: int) -> None:
    api.post(
        f"/customers/{ledger_customer}/transactions",
        {"type": "CREDIT", "amount": 50, "description": "Milk", "dueDate": "2030-01-01"},
    )
    status, body = api.post(
        f"/customers/{ledger_customer}/transactions",
        {
            "type": "PAYMENT",
            "amount": 10,
            "description": "Part payment",
            "dueDate": "2030-01-01",
        },
    )
    assert status == 400
    assert "cannot have a due date" in body["message"]


def test_a_payment_defaults_its_description(api: Api, new_customer) -> None:
    customer_id = new_customer("Default Description")
    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 100, "description": "Goods", "dueDate": "2030-01-01"},
    )
    status, body = api.post(
        f"/customers/{customer_id}/transactions", {"type": "PAYMENT", "amount": 40}
    )
    assert status == 201
    assert body["data"]["transaction"]["description"] == "Payment received"
    assert body["data"]["customer"]["balance"] == 60


def test_handles_cents_without_float_drift(api: Api, new_customer) -> None:
    customer_id = new_customer("Cents Test")

    for amount in (0.1, 0.2):
        api.post(
            f"/customers/{customer_id}/transactions",
            {"type": "CREDIT", "amount": amount, "description": "Sweet", "dueDate": "2030-01-01"},
        )

    _, after = api.get(f"/customers/{customer_id}")
    # 0.1 + 0.2 is 0.30000000000000004 in floating point. NUMERIC gives 0.30.
    assert after["data"]["balance"] == 0.3


def test_rejects_more_than_two_decimal_places(api: Api, new_customer) -> None:
    customer_id = new_customer("Precision Test")
    status, body = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 10.999, "description": "Odd", "dueDate": "2030-01-01"},
    )
    assert status == 400
    assert "two decimal places" in body["message"]


def test_reports_a_running_balance_on_the_customer_history(api: Api, new_customer) -> None:
    customer_id = new_customer("History Test")

    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 500, "description": "Groceries", "dueDate": "2030-01-01"},
    )
    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "PAYMENT", "amount": 200, "description": "Cash payment"},
    )

    _, history = api.get(f"/customers/{customer_id}/transactions")
    # Newest first: the payment leaves 300, the credit before it left 500.
    assert len(history["data"]["transactions"]) == 2
    assert history["data"]["transactions"][0]["runningBalance"] == 300
    assert history["data"]["transactions"][1]["runningBalance"] == 500
    assert history["data"]["customer"]["balance"] == 300


def test_recalculates_the_balance_when_a_transaction_is_deleted(api: Api, new_customer) -> None:
    customer_id = new_customer("Delete Test")

    _, created = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 750, "description": "Mistyped", "dueDate": "2030-01-01"},
    )
    assert created["data"]["customer"]["balance"] == 750

    status, _ = api.delete(f"/transactions/{created['data']['transaction']['id']}")
    assert status == 200

    _, after = api.get(f"/customers/{customer_id}")
    assert after["data"]["balance"] == 0


def test_marks_a_customer_overdue_once_a_due_date_has_passed(api: Api, new_customer) -> None:
    customer_id = new_customer("Overdue Test")
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "amount": 800,
            "description": "Late goods",
            "dueDate": yesterday,
        },
    )

    _, after = api.get(f"/customers/{customer_id}")
    assert after["data"]["status"] == "OVERDUE"
    assert after["data"]["dueDate"] == yesterday

    _, filtered = api.get("/customers?status=OVERDUE")
    assert any(c["id"] == customer_id for c in filtered["data"])


def test_fetches_one_transaction_by_id(api: Api, new_customer) -> None:
    customer_id = new_customer("Fetch By Id")
    _, created = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 120, "description": "Paraffin", "dueDate": "2030-01-01"},
    )
    transaction_id = created["data"]["transaction"]["id"]

    status, body = api.get(f"/transactions/{transaction_id}")
    assert status == 200
    assert body["data"]["amount"] == 120
    assert body["data"]["description"] == "Paraffin"
    assert body["data"]["customerName"] == "Fetch By Id"


def test_404s_for_a_transaction_that_does_not_exist(api: Api) -> None:
    assert api.get("/transactions/99999999")[0] == 404


def test_feed_filters_by_type(api: Api) -> None:
    _, body = api.get("/transactions?type=PAYMENT")
    assert body["data"]
    assert all(t["type"] == "PAYMENT" for t in body["data"])


def test_feed_filters_by_date_range(api: Api) -> None:
    today = date.today().isoformat()
    long_ago = "2000-01-01"

    status, todays = api.get(f"/transactions?from={today}&to={today}")
    assert status == 200
    assert todays["data"], "everything in this run was created today"

    # A window that closes before the app existed returns nothing.
    status, ancient = api.get(f"/transactions?from={long_ago}&to={long_ago}")
    assert status == 200
    assert ancient["data"] == []


def test_feed_rejects_a_malformed_date_filter(api: Api) -> None:
    status, _ = api.get("/transactions?from=not-a-date")
    assert status == 400
