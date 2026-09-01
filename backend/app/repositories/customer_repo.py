"""Customer SQL.

A customer's balance and status are never stored. They are derived from the
transaction ledger on every read, which is why CUSTOMER_SELECT below is shared
by every query that returns a customer — the same statement the Express
backend used, carried over unchanged.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# The one definition of what a customer's money looks like.
#
#   balance      = total credit - total payments
#   due_date     = the earliest unmet due date (what the owner should chase)
CUSTOMER_SELECT = """
  SELECT
    c.id,
    c.full_name,
    c.phone,
    c.email,
    c.address,
    c.gender,
    c.notes,
    c.created_at,
    c.updated_at,
    COALESCE(SUM(CASE WHEN t.type = 'CREDIT'  THEN t.amount ELSE 0 END), 0) AS total_credit,
    COALESCE(SUM(CASE WHEN t.type = 'PAYMENT' THEN t.amount ELSE 0 END), 0) AS total_paid,
    COALESCE(SUM(CASE WHEN t.type = 'CREDIT'  THEN t.amount ELSE -t.amount END), 0) AS balance,
    MIN(t.due_date) FILTER (WHERE t.type = 'CREDIT' AND t.due_date IS NOT NULL) AS due_date,
    COUNT(t.id) AS transaction_count
  FROM customers c
  LEFT JOIN transactions t ON t.customer_id = c.id
"""

GROUP_BY = " GROUP BY c.id "

_NON_DIGITS = re.compile(r"\D")

UPDATABLE_COLUMNS = {
    "fullName": "full_name",
    "phone": "phone",
    "email": "email",
    "address": "address",
    "gender": "gender",
    "notes": "notes",
}


def search_rows(db: Session, user_id: int, search: str = "") -> list[Any]:
    """`search` matches name or phone. Digits typed into the search box also
    match a phone stored with spaces ("0740998882" finds "074 099 8882")."""
    params: dict[str, Any] = {"user_id": user_id}
    where = " WHERE c.user_id = :user_id "

    term = (search or "").strip()
    if term:
        params["term"] = f"%{term}%"
        clauses = ["c.full_name ILIKE :term", "c.phone ILIKE :term"]

        # Only compare digit-only forms when the term actually contains digits.
        digits = _NON_DIGITS.sub("", term)
        if digits:
            params["digits"] = f"%{digits}%"
            clauses.append("regexp_replace(c.phone, '\\D', '', 'g') LIKE :digits")

        where += f" AND ({' OR '.join(clauses)}) "

    sql = f"{CUSTOMER_SELECT} {where} {GROUP_BY} ORDER BY c.full_name ASC"
    return db.execute(text(sql), params).mappings().all()


def find_row(db: Session, user_id: int, customer_id: int) -> Any | None:
    sql = f"{CUSTOMER_SELECT} WHERE c.user_id = :user_id AND c.id = :id {GROUP_BY}"
    return db.execute(text(sql), {"user_id": user_id, "id": customer_id}).mappings().first()


def insert(db: Session, user_id: int, data: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO customers (user_id, full_name, phone, email, address, gender, notes)
            VALUES (:user_id, :full_name, :phone, :email, :address, :gender, :notes)
            RETURNING id
            """
        ),
        {
            "user_id": user_id,
            "full_name": data["fullName"],
            "phone": data["phone"],
            "email": data.get("email"),
            "address": data.get("address"),
            "gender": data.get("gender"),
            "notes": data.get("notes"),
        },
    ).first()
    db.commit()
    return int(row[0])


def update_columns(db: Session, user_id: int, customer_id: int, patch: dict[str, Any]) -> bool:
    """Only the keys present in `patch` are written, so a partial update cannot
    blank out fields the caller did not mention."""
    sets: list[str] = []
    params: dict[str, Any] = {"user_id": user_id, "id": customer_id}

    for key, column in UPDATABLE_COLUMNS.items():
        if key in patch:
            params[column] = patch[key]
            sets.append(f"{column} = :{column}")

    if not sets:
        return True

    sets.append("updated_at = now()")
    sql = f"""
        UPDATE customers SET {', '.join(sets)}
        WHERE user_id = :user_id AND id = :id
        RETURNING id
    """
    row = db.execute(text(sql), params).first()
    db.commit()
    return row is not None


def delete(db: Session, user_id: int, customer_id: int) -> bool:
    """Transactions and reminders go with them (ON DELETE CASCADE)."""
    row = db.execute(
        text("DELETE FROM customers WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": customer_id},
    ).first()
    db.commit()
    return row is not None
