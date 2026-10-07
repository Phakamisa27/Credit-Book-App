"""Cash entry SQL (ThathaCash).

Like a customer's balance in the Credit Book, the shop's cash is never stored.
It is summed from cash_entries on every read, so it can never drift away from
the entries that produced it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.cash_entry import ALL_CASH_TYPES

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

    if type_ in ALL_CASH_TYPES:
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
          (SELECT restock_reserve FROM users WHERE id = :user_id) AS restock_reserve,
          (SELECT buffer_percent FROM users WHERE id = :user_id) AS buffer_percent,
          (SELECT cash_counted_at FROM users WHERE id = :user_id) AS cash_counted_at,
          COALESCE(SUM(
            CASE WHEN type IN ('OPENING', 'INCOME', 'RECOUNT_IN') THEN amount ELSE -amount END
          ), 0) AS cash_available,
          COALESCE(SUM(amount) FILTER (
            WHERE type = 'DRAW' AND entry_date >= date_trunc('month', CURRENT_DATE)
          ), 0) AS draws_this_month,
          COUNT(*) FILTER (
            WHERE type = 'DRAW' AND entry_date >= date_trunc('month', CURRENT_DATE)
          ) AS draws_this_month_count,
          COUNT(*) AS entry_count
        FROM cash_entries
        WHERE user_id = :user_id
    """
    return db.execute(text(sql), {"user_id": user_id}).mappings().first()


def stock_spend(db: Session, user_id: int, days: int) -> Any:
    """Stock bought in the last `days` days (today included): the total, and
    on how many different days it was bought."""
    sql = """
        SELECT
          COALESCE(SUM(amount), 0) AS total,
          COUNT(DISTINCT entry_date) AS days
        FROM cash_entries
        WHERE user_id = :user_id
          AND type = 'STOCK'
          AND entry_date >  CURRENT_DATE - CAST(:days AS integer)
          AND entry_date <= CURRENT_DATE
    """
    return db.execute(text(sql), {"user_id": user_id, "days": days}).mappings().first()


def find_row(db: Session, user_id: int, entry_id: int) -> Any | None:
    return (
        db.execute(
            text(f"SELECT {COLUMNS} FROM cash_entries WHERE user_id = :user_id AND id = :id"),
            {"user_id": user_id, "id": entry_id},
        )
        .mappings()
        .first()
    )


def _mark_counted(db: Session, user_id: int) -> None:
    """The owner has just confirmed the cash. Committed by the caller."""
    db.execute(text("UPDATE users SET cash_counted_at = now() WHERE id = :id"), {"id": user_id})


def insert(db: Session, user_id: int, data: dict[str, Any]) -> Any:
    row = _insert_row(db, user_id, data)
    # Entering starting cash IS counting it.
    if data["type"] == "OPENING":
        _mark_counted(db, user_id)
    db.commit()
    return row


def record_count(db: Session, user_id: int, difference: dict[str, Any] | None) -> None:
    """Saves a till count: the difference as a recount entry (if there is
    one), and the time — together, so neither can be saved without the other."""
    if difference is not None:
        _insert_row(db, user_id, difference)
    _mark_counted(db, user_id)
    db.commit()


def _insert_row(db: Session, user_id: int, data: dict[str, Any]) -> Any:
    return (
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


def delete(db: Session, user_id: int, entry_id: int) -> bool:
    row = db.execute(
        text("DELETE FROM cash_entries WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": entry_id},
    ).first()
    db.commit()
    return row is not None
