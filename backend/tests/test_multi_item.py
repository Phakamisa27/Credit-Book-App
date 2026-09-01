"""Multi-item credit transactions.

One customer taking bread, perfume, milk and airtime in a single visit must be
ONE transaction whose grand total moves the balance once — and that total is
computed on the server, never taken from the client.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from tests.conftest import Api

# The worked example from the brief: R254.00 in one visit.
EXAMPLE = [
    {"name": "Bread", "quantity": 2, "unitPrice": 15},
    {"name": "Perfume", "quantity": 1, "unitPrice": 120},
    {"name": "Milk", "quantity": 3, "unitPrice": 18},
    {"name": "Airtime", "quantity": 1, "unitPrice": 50},
]


# ------------------------------------------------------------- one item ----
def test_records_a_single_line_and_sets_the_total_from_it(api: Api, new_customer) -> None:
    customer_id = new_customer("Single Item")

    status, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [{"name": "Bread", "quantity": 2, "unitPrice": 15}],
        },
    )

    assert status == 201
    transaction = body["data"]["transaction"]
    assert len(transaction["items"]) == 1
    assert transaction["items"][0]["name"] == "Bread"
    assert transaction["items"][0]["quantity"] == 2
    assert transaction["items"][0]["unitPrice"] == 15
    assert transaction["items"][0]["lineTotal"] == 30
    assert transaction["amount"] == 30
    assert body["data"]["customer"]["balance"] == 30


def test_still_accepts_the_plain_amount_and_description_form(api: Api, new_customer) -> None:
    customer_id = new_customer("Legacy Form")

    status, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "amount": 250,
            "description": "Building sand",
            "dueDate": "2030-01-01",
        },
    )

    assert status == 201
    assert body["data"]["transaction"]["amount"] == 250
    assert body["data"]["transaction"]["items"] == []
    assert body["data"]["customer"]["balance"] == 250


# -------------------------------------------------------- multiple items ----
def test_records_four_items_as_one_transaction_totalling_254(api: Api, new_customer) -> None:
    customer_id = new_customer("John Example")

    status, body = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": EXAMPLE},
    )

    assert status == 201
    transaction = body["data"]["transaction"]

    assert len(transaction["items"]) == 4
    assert transaction["amount"] == 254
    assert transaction["itemCount"] == 4

    # Each line's own total.
    assert [i["lineTotal"] for i in transaction["items"]] == [30, 120, 54, 50]

    # Item order is preserved as entered.
    assert [i["name"] for i in transaction["items"]] == ["Bread", "Perfume", "Milk", "Airtime"]


def test_moves_the_balance_once_by_the_grand_total(api: Api, new_customer) -> None:
    customer_id = new_customer("Balance Once")

    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": EXAMPLE},
    )

    _, body = api.get(f"/customers/{customer_id}")
    assert body["data"]["balance"] == 254
    assert body["data"]["totalCredit"] == 254
    # One ledger entry, not four.
    assert body["data"]["transactionCount"] == 1


def test_auto_describes_the_transaction_from_its_items(api: Api, new_customer) -> None:
    customer_id = new_customer("Auto Describe")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": EXAMPLE},
    )

    assert body["data"]["transaction"]["description"] == "Bread ×2, Perfume, Milk ×3, Airtime"


def test_accepts_a_description_that_overrides_the_auto_summary(api: Api, new_customer) -> None:
    customer_id = new_customer("Custom Describe")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "description": "Month-end shop",
            "items": EXAMPLE,
        },
    )

    assert body["data"]["transaction"]["description"] == "Month-end shop"
    assert body["data"]["transaction"]["amount"] == 254


# ------------------------------------------------------------ calculation ----
def test_line_total_is_quantity_times_unit_price(api: Api, new_customer) -> None:
    customer_id = new_customer("Line Maths")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [
                {"name": "Cooldrink crate", "quantity": 8, "unitPrice": 220},
                {"name": "Maize meal 5kg", "quantity": 4, "unitPrice": 79.99},
            ],
        },
    )

    crate, maize = body["data"]["transaction"]["items"]
    assert crate["lineTotal"] == 1760  # 8 × 220
    assert maize["lineTotal"] == 319.96  # 4 × 79.99 — no float drift
    assert body["data"]["transaction"]["amount"] == 2079.96


def test_cent_level_prices_sum_exactly(api: Api, new_customer) -> None:
    customer_id = new_customer("Cents Maths")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            # 3 × 0.10 + 3 × 0.20 = 0.90, which naive floats get wrong.
            "items": [
                {"name": "Sweet A", "quantity": 3, "unitPrice": 0.1},
                {"name": "Sweet B", "quantity": 3, "unitPrice": 0.2},
            ],
        },
    )

    assert body["data"]["transaction"]["amount"] == 0.9
    assert body["data"]["customer"]["balance"] == 0.9


def test_a_client_supplied_amount_is_ignored_in_favour_of_the_items(
    api: Api, new_customer
) -> None:
    customer_id = new_customer("Ignore Client Total")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "amount": 5,  # a lie
            "items": [{"name": "Bread", "quantity": 2, "unitPrice": 15}],
        },
    )

    assert body["data"]["transaction"]["amount"] == 30
    assert body["data"]["customer"]["balance"] == 30


def test_the_database_itself_rejects_a_line_total_that_does_not_match(
    api: Api, new_customer
) -> None:
    customer_id = new_customer("DB Guard")
    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [{"name": "Bread", "quantity": 2, "unitPrice": 15}],
        },
    )
    transaction_id = body["data"]["transaction"]["id"]

    # Bypass the API and try to write a wrong line directly.
    with SessionLocal() as session, pytest.raises(IntegrityError) as caught:
        session.execute(
            text(
                """
                INSERT INTO transaction_items
                  (transaction_id, name, quantity, unit_price, line_total, position)
                VALUES (:tid, 'Fraud', 2, 10.00, 999.00, 1)
                """
            ),
            {"tid": transaction_id},
        )
        session.commit()

    assert "transaction_items_line_total_matches" in str(caught.value)


def test_the_database_rejects_a_zero_quantity_line(api: Api, new_customer) -> None:
    """A zero quantity can never produce a valid row: the guards on `quantity`
    and on `line_total` both stand in the way, whichever Postgres reports
    first."""
    customer_id = new_customer("DB Quantity Guard")
    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [{"name": "Bread", "quantity": 1, "unitPrice": 15}],
        },
    )
    transaction_id = body["data"]["transaction"]["id"]

    with SessionLocal() as session, pytest.raises(IntegrityError) as caught:
        session.execute(
            text(
                """
                INSERT INTO transaction_items
                  (transaction_id, name, quantity, unit_price, line_total, position)
                VALUES (:tid, 'Nothing', 0, 10.00, 0.00, 1)
                """
            ),
            {"tid": transaction_id},
        )
        session.commit()

    message = str(caught.value)
    assert "violates check constraint" in message
    assert "transaction_items_" in message


# ------------------------------------------------------------- item rows ----
def test_records_exactly_the_rows_that_were_submitted(api: Api, new_customer) -> None:
    customer_id = new_customer("Row Count")

    # The UI added five rows and the owner removed the third before saving,
    # so only four arrive.
    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [
                {"name": "Bread", "quantity": 1, "unitPrice": 15},
                {"name": "Milk", "quantity": 1, "unitPrice": 18},
                {"name": "Airtime", "quantity": 1, "unitPrice": 50},
                {"name": "Soap", "quantity": 1, "unitPrice": 22},
            ],
        },
    )

    items = body["data"]["transaction"]["items"]
    assert len(items) == 4
    assert not any(i["name"] == "Perfume" for i in items)
    assert body["data"]["transaction"]["amount"] == 105


def test_deleting_the_transaction_removes_its_item_rows(api: Api, new_customer) -> None:
    customer_id = new_customer("Cascade Items")

    _, body = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [
                {"name": "Bread", "quantity": 2, "unitPrice": 15},
                {"name": "Milk", "quantity": 3, "unitPrice": 18},
            ],
        },
    )
    transaction_id = body["data"]["transaction"]["id"]

    assert _item_row_count(transaction_id) == 2

    api.delete(f"/transactions/{transaction_id}")

    assert _item_row_count(transaction_id) == 0

    _, customer = api.get(f"/customers/{customer_id}")
    assert customer["data"]["balance"] == 0


def _item_row_count(transaction_id: int) -> int:
    with SessionLocal() as session:
        return session.execute(
            text("SELECT COUNT(*) FROM transaction_items WHERE transaction_id = :tid"),
            {"tid": transaction_id},
        ).scalar_one()


# ------------------------------------------------------------ validation ----
@pytest.fixture(scope="module")
def validation_target(new_customer) -> int:
    return new_customer("Validation Target")


def _reject(api: Api, customer_id: int, items, fragment: str) -> None:
    status, body = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": items},
    )
    assert status == 400, f"expected 400, got {status}: {body}"
    assert fragment.lower() in body["message"].lower(), body["message"]


def test_rejects_an_empty_item_list(api: Api, validation_target: int) -> None:
    _reject(api, validation_target, [], "at least one item")


def test_rejects_a_quantity_of_zero(api: Api, validation_target: int) -> None:
    _reject(api, validation_target, [{"name": "Bread", "quantity": 0, "unitPrice": 15}], "at least 1")


def test_rejects_a_negative_quantity(api: Api, validation_target: int) -> None:
    _reject(
        api, validation_target, [{"name": "Bread", "quantity": -2, "unitPrice": 15}], "at least 1"
    )


def test_rejects_a_fractional_quantity(api: Api, validation_target: int) -> None:
    _reject(
        api,
        validation_target,
        [{"name": "Bread", "quantity": 1.5, "unitPrice": 15}],
        "whole number",
    )


def test_rejects_a_zero_unit_price(api: Api, validation_target: int) -> None:
    _reject(
        api,
        validation_target,
        [{"name": "Bread", "quantity": 1, "unitPrice": 0}],
        "greater than zero",
    )


def test_rejects_a_negative_unit_price(api: Api, validation_target: int) -> None:
    _reject(
        api,
        validation_target,
        [{"name": "Bread", "quantity": 1, "unitPrice": -15}],
        "greater than zero",
    )


def test_rejects_a_unit_price_with_too_many_decimals(api: Api, validation_target: int) -> None:
    _reject(
        api,
        validation_target,
        [{"name": "Bread", "quantity": 1, "unitPrice": 15.999}],
        "two decimal places",
    )


def test_rejects_a_blank_item_name(api: Api, validation_target: int) -> None:
    _reject(api, validation_target, [{"name": "   ", "quantity": 1, "unitPrice": 15}], "name is required")


def test_names_the_offending_row_so_a_long_form_is_fixable(
    api: Api, validation_target: int
) -> None:
    _reject(
        api,
        validation_target,
        [
            {"name": "Bread", "quantity": 1, "unitPrice": 15},
            {"name": "Perfume", "quantity": 0, "unitPrice": 120},
        ],
        "Item 2 (Perfume)",
    )


def test_rejects_items_sent_as_something_other_than_a_list(
    api: Api, validation_target: int
) -> None:
    status, body = api.post(
        f"/customers/{validation_target}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": "Bread"},
    )
    assert status == 400
    assert "must be a list" in body["message"]


def test_rejects_item_lines_on_a_payment(api: Api, validation_target: int) -> None:
    status, body = api.post(
        f"/customers/{validation_target}/transactions",
        {"type": "PAYMENT", "items": [{"name": "Bread", "quantity": 1, "unitPrice": 15}]},
    )
    assert status == 400
    assert "payment cannot have item lines" in body["message"].lower()


def test_writes_nothing_when_validation_fails(api: Api, validation_target: int) -> None:
    """Every rejection above ran against this customer. Not one of them may
    have left a transaction or an item row behind."""
    _, body = api.get(f"/customers/{validation_target}")
    assert body["data"]["balance"] == 0
    assert body["data"]["transactionCount"] == 0


def test_a_failure_partway_through_the_items_rolls_the_whole_thing_back(
    api: Api, new_customer
) -> None:
    """The last line is invalid, so the header and the two good lines that were
    already validated must not survive."""
    customer_id = new_customer("Rollback Target")

    status, _ = api.post(
        f"/customers/{customer_id}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [
                {"name": "Bread", "quantity": 2, "unitPrice": 15},
                {"name": "Milk", "quantity": 3, "unitPrice": 18},
                {"name": "Broken", "quantity": 1, "unitPrice": -1},
            ],
        },
    )
    assert status == 400

    _, body = api.get(f"/customers/{customer_id}/transactions")
    assert body["data"]["transactions"] == []
    assert body["data"]["customer"]["balance"] == 0


# ------------------------------------------------- payments and history ----
@pytest.fixture(scope="module")
def pays_multi(api: Api, new_customer) -> int:
    customer_id = new_customer("Pays Multi")
    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": EXAMPLE},
    )
    return customer_id


def test_a_part_payment_reduces_the_grand_total(api: Api, pays_multi: int) -> None:
    status, body = api.post(
        f"/customers/{pays_multi}/transactions",
        {"type": "PAYMENT", "amount": 54, "description": "Part payment"},
    )
    assert status == 201
    assert body["data"]["customer"]["balance"] == 200  # 254 - 54


def test_overpaying_the_grand_total_is_refused(api: Api, pays_multi: int) -> None:
    status, body = api.post(
        f"/customers/{pays_multi}/transactions",
        {"type": "PAYMENT", "amount": 250, "description": "Too much"},
    )
    assert status == 400
    assert "more than the balance owed (R200.00)" in body["message"]


def test_settling_the_remainder_clears_the_account(api: Api, pays_multi: int) -> None:
    status, _ = api.post(
        f"/customers/{pays_multi}/transactions",
        {"type": "PAYMENT", "amount": 200, "description": "Settled"},
    )
    assert status == 201

    _, body = api.get(f"/customers/{pays_multi}")
    assert body["data"]["balance"] == 0
    assert body["data"]["status"] == "PAID"
    assert body["data"]["totalCredit"] == 254
    assert body["data"]["totalPaid"] == 254


def test_a_payment_carries_no_item_rows(api: Api, pays_multi: int) -> None:
    _, body = api.get(f"/customers/{pays_multi}/transactions")
    payment = next(t for t in body["data"]["transactions"] if t["type"] == "PAYMENT")
    assert payment["items"] == []
    assert payment["itemCount"] == 0


def test_history_returns_each_line_with_its_own_quantity_and_totals(
    api: Api, new_customer
) -> None:
    customer_id = new_customer("History Items")

    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "dueDate": "2030-01-01", "items": EXAMPLE},
    )
    api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "PAYMENT", "amount": 54, "description": "Cash payment"},
    )

    _, body = api.get(f"/customers/{customer_id}/transactions")
    history = body["data"]["transactions"]

    assert len(history) == 2

    # Newest first: the payment, then the multi-item credit.
    assert history[0]["type"] == "PAYMENT"
    assert history[0]["runningBalance"] == 200

    credit = history[1]
    assert credit["type"] == "CREDIT"
    assert credit["amount"] == 254
    assert credit["runningBalance"] == 254
    assert len(credit["items"]) == 4
    assert [
        [i["name"], i["quantity"], i["unitPrice"], i["lineTotal"]] for i in credit["items"]
    ] == [
        ["Bread", 2, 15, 30],
        ["Perfume", 1, 120, 120],
        ["Milk", 3, 18, 54],
        ["Airtime", 1, 50, 50],
    ]

    # Line totals reconcile to the transaction total.
    assert sum(i["lineTotal"] for i in credit["items"]) == credit["amount"]


def test_the_business_wide_feed_carries_items_too(api: Api) -> None:
    _, body = api.get("/transactions")
    multi = next((t for t in body["data"] if t["itemCount"] == 4), None)
    assert multi is not None, "expected a four-item transaction in the feed"
    assert len(multi["items"]) == 4
    assert multi["amount"] == 254


def test_a_single_transaction_fetched_by_id_carries_its_items(api: Api) -> None:
    _, feed = api.get("/transactions")
    multi = next(t for t in feed["data"] if t["itemCount"] == 4)

    _, body = api.get(f"/transactions/{multi['id']}")
    assert len(body["data"]["items"]) == 4
    assert body["data"]["amount"] == 254


# -------------------------------------------------- nothing else broke ----
def test_outstanding_total_matches_the_sum_of_positive_balances(api: Api) -> None:
    _, customers = api.get("/customers")
    expected = sum(c["balance"] for c in customers["data"] if c["balance"] > 0)

    _, summary = api.get("/reports/summary")
    assert round(summary["data"]["totalOutstanding"] * 100) == round(expected * 100)


def test_total_credit_issued_matches_the_sum_of_transaction_totals(api: Api) -> None:
    _, feed = api.get("/transactions?type=CREDIT")
    expected = sum(t["amount"] for t in feed["data"])

    _, summary = api.get("/reports/summary")
    assert round(summary["data"]["totalCreditIssued"] * 100) == round(expected * 100)
