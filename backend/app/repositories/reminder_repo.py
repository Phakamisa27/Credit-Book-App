"""Reminder SQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.reminder import STATUSES

BASE_SELECT = """
  SELECT r.id, r.customer_id, r.amount, r.due_date, r.status, r.notes,
         r.created_at, r.updated_at,
         c.full_name AS customer_name, c.phone AS customer_phone
  FROM reminders r
  JOIN customers c ON c.id = r.customer_id
"""

UPDATABLE_COLUMNS = {
    "amount": "amount",
    "dueDate": "due_date",
    "status": "status",
    "notes": "notes",
}


def list_rows(db: Session, user_id: int, *, status: str = "", customer_id: int | None = None):
    params: dict[str, Any] = {"user_id": user_id}
    where = " WHERE r.user_id = :user_id "

    wanted = str(status or "").strip().upper()
    if wanted in STATUSES:
        params["status"] = wanted
        where += " AND r.status = :status "
    elif wanted == "OPEN":
        where += " AND r.status IN ('PENDING', 'SENT') "

    if customer_id:
        params["customer_id"] = customer_id
        where += " AND r.customer_id = :customer_id "

    # Soonest first — the top of the list is what needs attention today.
    sql = f"{BASE_SELECT} {where} ORDER BY r.due_date ASC, r.id ASC"
    return db.execute(text(sql), params).mappings().all()


def find_row(db: Session, user_id: int, reminder_id: int) -> Any | None:
    sql = f"{BASE_SELECT} WHERE r.user_id = :user_id AND r.id = :id"
    return db.execute(text(sql), {"user_id": user_id, "id": reminder_id}).mappings().first()


def customer_belongs_to(db: Session, user_id: int, customer_id: int) -> bool:
    row = db.execute(
        text("SELECT id FROM customers WHERE user_id = :user_id AND id = :id"),
        {"user_id": user_id, "id": customer_id},
    ).first()
    return row is not None


def insert(db: Session, user_id: int, data: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO reminders (user_id, customer_id, amount, due_date, status, notes)
            VALUES (:user_id, :customer_id, :amount, :due_date, :status, :notes)
            RETURNING id
            """
        ),
        {
            "user_id": user_id,
            "customer_id": data["customerId"],
            "amount": data["amount"],
            "due_date": data["dueDate"],
            "status": data.get("status") or "PENDING",
            "notes": data.get("notes"),
        },
    ).first()
    db.commit()
    return int(row[0])


def update_columns(db: Session, user_id: int, reminder_id: int, patch: dict[str, Any]) -> bool:
    sets: list[str] = []
    params: dict[str, Any] = {"user_id": user_id, "id": reminder_id}

    for key, column in UPDATABLE_COLUMNS.items():
        if key in patch:
            params[column] = patch[key]
            sets.append(f"{column} = :{column}")

    if not sets:
        return True

    sets.append("updated_at = now()")
    sql = f"""
        UPDATE reminders SET {', '.join(sets)}
        WHERE user_id = :user_id AND id = :id
        RETURNING id
    """
    row = db.execute(text(sql), params).first()
    db.commit()
    return row is not None


def delete(db: Session, user_id: int, reminder_id: int) -> bool:
    row = db.execute(
        text("DELETE FROM reminders WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": reminder_id},
    ).first()
    db.commit()
    return row is not None
