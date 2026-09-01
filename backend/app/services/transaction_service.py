"""The ledger.

A transaction is one ledger entry. A CREDIT may carry line items — bread, milk
and airtime taken in one visit are ONE transaction with three items, and the
customer's balance moves once, by the grand total.

The grand total is always computed here from the line items, in Decimal. A
total sent by the client is ignored, so the books cannot be talked into
disagreeing with the items that produced them.

Business rule: a payment may not exceed what the customer owes. The books track
debt, not deposits, so a negative balance would be a data entry mistake rather
than a real state. Overpayments are rejected with a message telling the owner
exactly what the balance is.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import format_rand, quantize, to_amount
from app.core.serialize import date_only, iso_utc
from app.repositories import transaction_repo


def item_to_api(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "quantity": int(row["quantity"]),
        "unitPrice": to_amount(row["unit_price"]),
        "lineTotal": to_amount(row["line_total"]),
    }


def to_api(row: Any, items: list[Any] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    items = items or []

    payload: dict[str, Any] = {
        "id": row["id"],
        "customerId": row["customer_id"],
        "customerName": row["customer_name"],
        "type": row["type"],
        "amount": to_amount(row["amount"]),
        "description": row["description"],
        "dueDate": date_only(row["due_date"]) if row["due_date"] else None,
        "notes": row["notes"],
        "signature": row["signature"] or None,
        "productPhoto": row["product_photo"] or None,
        "items": [item_to_api(item) for item in items],
        "itemCount": len(items),
        "createdAt": iso_utc(row["created_at"]),
    }

    # Present only on the customer-profile query, which computes it.
    if "running_balance" in row.keys():
        payload["runningBalance"] = to_amount(row["running_balance"])

    return payload


def _attach_items(db: Session, rows: list[Any]) -> list[dict[str, Any]]:
    grouped = transaction_repo.load_items_for(db, [row["id"] for row in rows])
    return [to_api(row, grouped.get(row["id"], [])) for row in rows]


def list_for_user(db: Session, user_id: int, **filters: Any) -> list[dict[str, Any]]:
    rows = transaction_repo.list_for_user(db, user_id, **filters)
    return _attach_items(db, list(rows))


def list_for_customer(db: Session, user_id: int, customer_id: int) -> list[dict[str, Any]]:
    rows = transaction_repo.list_for_customer(db, user_id, customer_id)
    return _attach_items(db, list(rows))


def find_by_id(db: Session, user_id: int, transaction_id: int) -> dict[str, Any] | None:
    row = transaction_repo.find_row(db, user_id, transaction_id)
    if row is None:
        return None
    grouped = transaction_repo.load_items_for(db, [row["id"]])
    return to_api(row, grouped.get(row["id"], []))


def summarise_items(items: list[dict[str, Any]]) -> str:
    """Builds a readable one-line summary for the feed, e.g.
    "Bread ×2, Perfume, Milk ×3" — so a multi-item credit still reads well
    anywhere a single description is shown."""
    parts = [
        f"{item['name']} ×{item['quantity']}" if item["quantity"] > 1 else item["name"]
        for item in items
    ]
    summary = ", ".join(parts)
    if len(summary) <= 200:
        return summary
    return f"{len(parts)} items"


def create(db: Session, user_id: int, customer_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Creates the transaction and all of its item rows inside ONE database
    transaction, holding a row lock on the customer. Either everything is
    written or nothing is."""
    try:
        customer = transaction_repo.lock_customer(db, user_id, customer_id)
        if customer is None:
            raise ApiError.not_found("Customer not found.")

        line_items: list[dict[str, Any]] = data.get("items") or []

        # The grand total is derived from the items, never taken from the client.
        if line_items:
            total = Decimal("0")
            for item in line_items:
                # Integer quantity × a cents-exact unit price stays exact.
                total += Decimal(item["quantity"]) * item["unitPrice"]
            amount = quantize(total)
            description = data.get("description") or summarise_items(line_items)
        else:
            amount = quantize(data["amount"])
            description = data.get("description")

        if not amount > 0:
            raise ApiError.bad_request("The transaction total must be greater than zero.")

        if data["type"] == "PAYMENT":
            balance = quantize(transaction_repo.balance_for_customer(db, customer_id))

            if balance <= 0:
                raise ApiError.bad_request(
                    f"{customer['full_name']} does not owe anything, "
                    "so there is nothing to pay off."
                )
            if amount > balance:
                raise ApiError.bad_request(
                    f"Payment is more than the balance owed (R{format_rand(balance)}). "
                    "Enter that amount or less."
                )

        transaction_id = transaction_repo.insert_transaction(
            db,
            {
                "user_id": user_id,
                "customer_id": customer_id,
                "type": data["type"],
                "amount": amount,
                "description": description,
                "due_date": data.get("dueDate"),
                "notes": data.get("notes"),
                "signature": data.get("signature"),
                "product_photo": data.get("productPhoto"),
            },
        )

        for position, item in enumerate(line_items):
            line_total = quantize(Decimal(item["quantity"]) * item["unitPrice"])
            transaction_repo.insert_item(
                db,
                {
                    "transaction_id": transaction_id,
                    "name": item["name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unitPrice"],
                    "line_total": line_total,
                    "position": position,
                },
            )

        row = transaction_repo.find_row_by_id(db, transaction_id)
        grouped = transaction_repo.load_items_for(db, [transaction_id])
        result = to_api(row, grouped.get(transaction_id, []))

        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def remove(db: Session, user_id: int, transaction_id: int) -> None:
    """Deleting is allowed — the owner will occasionally mistype an amount.
    Because the balance is derived, removing the row is all that is needed to
    correct it. Line items go with it (ON DELETE CASCADE)."""
    if not transaction_repo.delete(db, user_id, transaction_id):
        raise ApiError.not_found("Transaction not found.")
