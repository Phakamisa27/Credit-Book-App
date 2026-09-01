"""Transaction (ledger) SQL.

The aggregate and window-function statements are carried over verbatim from the
Express backend — they are the part of the port most likely to change a number
if re-expressed, so they are not re-expressed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

BASE_SELECT = """
  SELECT t.id, t.customer_id, t.type, t.amount, t.description, t.due_date,
         t.notes, t.signature, t.product_photo, t.created_at,
         c.full_name AS customer_name
  FROM transactions t
  JOIN customers c ON c.id = t.customer_id
"""

MAX_LIMIT = 1000
DEFAULT_LIMIT = 200


def load_items_for(db: Session, transaction_ids: list[int]) -> dict[int, list[Any]]:
    """Loads the items for a set of transactions in one query and groups them by
    transaction id — avoids a query per row when rendering a long feed."""
    grouped: dict[int, list[Any]] = {}
    if not transaction_ids:
        return grouped

    rows = (
        db.execute(
            text(
                """
                SELECT id, transaction_id, name, quantity, unit_price, line_total
                FROM transaction_items
                WHERE transaction_id = ANY(:ids)
                ORDER BY transaction_id, position, id
                """
            ),
            {"ids": transaction_ids},
        )
        .mappings()
        .all()
    )

    for row in rows:
        grouped.setdefault(row["transaction_id"], []).append(row)
    return grouped


def list_for_user(
    db: Session,
    user_id: int,
    *,
    type_: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: Any = DEFAULT_LIMIT,
) -> list[Any]:
    """Whole-business feed, newest first. Supports the transactions page filters."""
    params: dict[str, Any] = {"user_id": user_id}
    where = " WHERE t.user_id = :user_id "

    wanted_type = str(type_ or "").strip().upper()
    if wanted_type in ("CREDIT", "PAYMENT"):
        params["type"] = wanted_type
        where += " AND t.type = :type "
    if date_from:
        params["date_from"] = date_from
        where += " AND t.created_at >= CAST(:date_from AS date) "
    if date_to:
        params["date_to"] = date_to
        # The whole of the "to" day, not just its midnight.
        where += " AND t.created_at < (CAST(:date_to AS date) + INTERVAL '1 day') "

    try:
        wanted_limit = int(limit)
    except (TypeError, ValueError):
        wanted_limit = DEFAULT_LIMIT
    if wanted_limit <= 0:
        wanted_limit = DEFAULT_LIMIT
    params["limit"] = min(wanted_limit, MAX_LIMIT)

    sql = f"{BASE_SELECT} {where} ORDER BY t.created_at DESC, t.id DESC LIMIT :limit"
    return db.execute(text(sql), params).mappings().all()


def list_for_customer(db: Session, user_id: int, customer_id: int) -> list[Any]:
    """One customer's history, newest first, each row carrying the balance as it
    stood immediately after that transaction — the "Balance" column on the
    customer profile. The window function sums oldest-to-newest; the outer
    query then flips the order for display."""
    return (
        db.execute(
            text(
                """
                SELECT * FROM (
                  SELECT t.id, t.customer_id, t.type, t.amount, t.description, t.due_date,
                         t.notes, t.signature, t.product_photo, t.created_at,
                         c.full_name AS customer_name,
                         SUM(CASE WHEN t.type = 'CREDIT' THEN t.amount ELSE -t.amount END)
                           OVER (ORDER BY t.created_at ASC, t.id ASC
                                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                           AS running_balance
                  FROM transactions t
                  JOIN customers c ON c.id = t.customer_id
                  WHERE t.user_id = :user_id AND t.customer_id = :customer_id
                ) ordered
                ORDER BY created_at DESC, id DESC
                """
            ),
            {"user_id": user_id, "customer_id": customer_id},
        )
        .mappings()
        .all()
    )


def find_row(db: Session, user_id: int, transaction_id: int) -> Any | None:
    sql = f"{BASE_SELECT} WHERE t.user_id = :user_id AND t.id = :id"
    return db.execute(text(sql), {"user_id": user_id, "id": transaction_id}).mappings().first()


def find_row_by_id(db: Session, transaction_id: int) -> Any | None:
    sql = f"{BASE_SELECT} WHERE t.id = :id"
    return db.execute(text(sql), {"id": transaction_id}).mappings().first()


def lock_customer(db: Session, user_id: int, customer_id: int) -> Any | None:
    """Row lock on the customer. Without it two payments submitted at the same
    moment could each read the old balance and both be accepted, together
    overpaying the debt."""
    return (
        db.execute(
            text(
                "SELECT id, full_name FROM customers "
                "WHERE user_id = :user_id AND id = :id FOR UPDATE"
            ),
            {"user_id": user_id, "id": customer_id},
        )
        .mappings()
        .first()
    )


def balance_for_customer(db: Session, customer_id: int) -> Decimal:
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END), 0)
                   AS balance
            FROM transactions WHERE customer_id = :customer_id
            """
        ),
        {"customer_id": customer_id},
    ).first()
    return Decimal(row[0] if row and row[0] is not None else 0)


def insert_transaction(db: Session, values: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO transactions
              (user_id, customer_id, type, amount, description, due_date, notes,
               signature, product_photo)
            VALUES
              (:user_id, :customer_id, :type, :amount, :description, :due_date, :notes,
               :signature, :product_photo)
            RETURNING id
            """
        ),
        values,
    ).first()
    return int(row[0])


def insert_item(db: Session, values: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO transaction_items
              (transaction_id, name, quantity, unit_price, line_total, position)
            VALUES
              (:transaction_id, :name, :quantity, :unit_price, :line_total, :position)
            """
        ),
        values,
    )


def delete(db: Session, user_id: int, transaction_id: int) -> bool:
    row = db.execute(
        text("DELETE FROM transactions WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": transaction_id},
    ).first()
    db.commit()
    return row is not None
