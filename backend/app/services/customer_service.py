"""Customer business rules.

Balance and status are derived, never stored, so `to_api` is the single place
that decides what a customer's money looks like to the outside world:

    balance  = total credit - total payments
    status   = PAID    when nothing is owed
               OVERDUE when money is owed and a due date has passed
               OWING   otherwise
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import to_amount
from app.core.serialize import date_only, iso_utc
from app.repositories import customer_repo


def derive_status(balance: float, due_date: str | None) -> str:
    if balance <= 0:
        return "PAID"
    if due_date and date.fromisoformat(due_date[:10]) < date.today():
        return "OVERDUE"
    return "OWING"


def to_api(row: Any) -> dict[str, Any] | None:
    """Converts a DB row into the shape the API returns. Money becomes a JSON
    number, dates become plain YYYY-MM-DD strings the frontend can print
    without timezone surprises."""
    if row is None:
        return None

    balance = to_amount(row["balance"])
    due_date = date_only(row["due_date"]) if row["due_date"] else None

    return {
        "id": row["id"],
        "fullName": row["full_name"],
        "phone": row["phone"],
        "email": row["email"],
        "address": row["address"],
        "gender": row["gender"],
        "notes": row["notes"],
        "balance": balance,
        "totalCredit": to_amount(row["total_credit"]),
        "totalPaid": to_amount(row["total_paid"]),
        "transactionCount": int(row["transaction_count"] or 0),
        "dueDate": due_date,
        "status": derive_status(balance, due_date),
        "createdAt": iso_utc(row["created_at"]),
        "updatedAt": iso_utc(row["updated_at"]),
    }


def list_customers(
    db: Session, user_id: int, *, search: str = "", status: str = ""
) -> list[dict[str, Any]]:
    rows = customer_repo.search_rows(db, user_id, search)
    customers = [to_api(row) for row in rows]

    # Status is derived in Python (it depends on "today"), so filter after mapping.
    wanted = (status or "").strip().upper()
    if wanted and wanted != "ALL":
        return [c for c in customers if c["status"] == wanted]
    return customers


def find_by_id(db: Session, user_id: int, customer_id: int) -> dict[str, Any] | None:
    return to_api(customer_repo.find_row(db, user_id, customer_id))


def find_by_id_or_fail(db: Session, user_id: int, customer_id: int) -> dict[str, Any]:
    """Raises instead of returning None — used by routes that cannot continue
    without the customer (e.g. recording a transaction against them)."""
    customer = find_by_id(db, user_id, customer_id)
    if customer is None:
        raise ApiError.not_found("Customer not found.")
    return customer


def create(db: Session, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    customer_id = customer_repo.insert(db, user_id, data)
    return find_by_id(db, user_id, customer_id)


def update(db: Session, user_id: int, customer_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    if not patch:
        return find_by_id_or_fail(db, user_id, customer_id)

    if not customer_repo.update_columns(db, user_id, customer_id, patch):
        raise ApiError.not_found("Customer not found.")
    return find_by_id(db, user_id, customer_id)


def remove(db: Session, user_id: int, customer_id: int) -> None:
    if not customer_repo.delete(db, user_id, customer_id):
        raise ApiError.not_found("Customer not found.")
