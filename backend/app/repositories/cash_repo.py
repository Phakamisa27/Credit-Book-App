"""Cash entry SQL (ThathaCash).

Like a customer's balance in the Credit Book, the shop's cash is never stored.
It is summed from cash_entries on every read, so it can never drift away from
the entries that produced it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.cash_entry import CASH_TYPES

COLUMNS = "id, type, amount, note, entry_date, created_at"

MAX_LIMIT = 1000
DEFAULT_LIMIT = 200


def _period_filter(date_from: str, date_to: str, params: dict[str, Any]) -> str:
    """Adds an inclusive YYYY-MM-DD range to a WHERE clause."""
    where = ""
    if date_from:
        params["date_from"] = date_from
        where += " AND entry_date >= CAST(:date_from AS date) "
    if date_to:
        params["date_to"] = date_to
        where += " AND entry_date <= CAST(:date_to AS date) "
    return where


def list_rows(
    db: Session,
    user_id: int,
    *,
    type_: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = DEFAULT_LIMIT,
) -> list[Any]:
    """Newest first."""
    params: dict[str, Any] = {"user_id": user_id, "limit": min(max(limit, 1), MAX_LIMIT)}
    where = " WHERE user_id = :user_id "

    if type_ in CASH_TYPES:
        params["type"] = type_
        where += " AND type = :type "
    where += _period_filter(date_from, date_to, params)

    sql = f"""
        SELECT {COLUMNS} FROM cash_entries {where}
        ORDER BY entry_date DESC, created_at DESC, id DESC
        LIMIT :limit
    """
    return db.execute(text(sql), params).mappings().all()


def totals(db: Session, user_id: int, *, date_from: str = "", date_to: str = "") -> Any:
    """How much of each type moved in the period."""
    params: dict[str, Any] = {"user_id": user_id}
    where = " WHERE user_id = :user_id " + _period_filter(date_from, date_to, params)

    sql = f"""
        SELECT
          COALESCE(SUM(amount) FILTER (WHERE type = 'OPENING'), 0) AS opening,
          COALESCE(SUM(amount) FILTER (WHERE type = 'INCOME'),  0) AS income,
          COALESCE(SUM(amount) FILTER (WHERE type = 'EXPENSE'), 0) AS expenses,
          COALESCE(SUM(amount) FILTER (WHERE type = 'STOCK'),   0) AS stock,
          COALESCE(SUM(amount) FILTER (WHERE type = 'DRAW'),    0) AS draws
        FROM cash_entries {where}
    """
    return db.execute(text(sql), params).mappings().first()


def cash_position(db: Session, user_id: int) -> Any:
    """All-time cash, plus the figures the Home screen needs alongside it."""
    sql = """
        SELECT
          COALESCE(SUM(CASE WHEN type IN ('OPENING', 'INCOME') THEN amount ELSE -amount END), 0)
            AS cash_available,
          COALESCE(SUM(amount) FILTER (
            WHERE type = 'DRAW' AND entry_date >= date_trunc('month', CURRENT_DATE)
          ), 0) AS draws_this_month,
          COUNT(*) AS entry_count
        FROM cash_entries
        WHERE user_id = :user_id
    """
    return db.execute(text(sql), {"user_id": user_id}).mappings().first()


def find_row(db: Session, user_id: int, entry_id: int) -> Any | None:
    return (
        db.execute(
            text(f"SELECT {COLUMNS} FROM cash_entries WHERE user_id = :user_id AND id = :id"),
            {"user_id": user_id, "id": entry_id},
        )
        .mappings()
        .first()
    )


def insert(db: Session, user_id: int, data: dict[str, Any]) -> Any:
    row = (
        db.execute(
            text(
                f"""
                INSERT INTO cash_entries (user_id, type, amount, note, entry_date)
                VALUES (:user_id, :type, :amount, :note, COALESCE(CAST(:entry_date AS date), CURRENT_DATE))
                RETURNING {COLUMNS}
                """
            ),
            {
                "user_id": user_id,
                "type": data["type"],
                "amount": data["amount"],
                "note": data.get("note"),
                "entry_date": data.get("date"),
            },
        )
        .mappings()
        .first()
    )
    db.commit()
    return row


def delete(db: Session, user_id: int, entry_id: int) -> bool:
    row = db.execute(
        text("DELETE FROM cash_entries WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": entry_id},
    ).first()
    db.commit()
    return row is not None
