"""Payment reminders.

Deliberately simple: a reminder is a note-to-self with a due date. There is no
scheduler, no email queue, no push infrastructure. The owner opens the
reminders page, sees who to chase, and sends a WhatsApp or SMS by hand.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import to_amount
from app.core.serialize import date_only, iso_utc
from app.models.reminder import STATUSES
from app.repositories import reminder_repo

__all__ = ["STATUSES", "derive_urgency", "to_api", "list_reminders", "find_by_id", "create",
           "update", "remove"]


def derive_urgency(due_date: str, status: str) -> str:
    """How urgent a reminder is, relative to today. Purely derived — the owner
    never has to mark something overdue themselves."""
    if status in ("DONE", "CANCELLED"):
        return "CLOSED"

    days = (date.fromisoformat(due_date[:10]) - date.today()).days

    if days < 0:
        return "OVERDUE"
    if days == 0:
        return "DUE_TODAY"
    if days <= 7:
        return "DUE_SOON"
    return "UPCOMING"


def to_api(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    due_date = date_only(row["due_date"])
    return {
        "id": row["id"],
        "customerId": row["customer_id"],
        "customerName": row["customer_name"],
        "customerPhone": row["customer_phone"],
        "amount": to_amount(row["amount"]),
        "dueDate": due_date,
        "status": row["status"],
        "urgency": derive_urgency(due_date, row["status"]),
        "notes": row["notes"],
        "createdAt": iso_utc(row["created_at"]),
        "updatedAt": iso_utc(row["updated_at"]),
    }


def list_reminders(
    db: Session, user_id: int, *, status: str = "", customer_id: int | None = None
) -> list[dict[str, Any]]:
    rows = reminder_repo.list_rows(db, user_id, status=status, customer_id=customer_id)
    return [to_api(row) for row in rows]


def find_by_id(db: Session, user_id: int, reminder_id: int) -> dict[str, Any] | None:
    return to_api(reminder_repo.find_row(db, user_id, reminder_id))


def create(db: Session, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    if not reminder_repo.customer_belongs_to(db, user_id, data["customerId"]):
        raise ApiError.not_found("Customer not found.")

    reminder_id = reminder_repo.insert(db, user_id, data)
    return find_by_id(db, user_id, reminder_id)


def update(db: Session, user_id: int, reminder_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    if not patch:
        existing = find_by_id(db, user_id, reminder_id)
        if existing is None:
            raise ApiError.not_found("Reminder not found.")
        return existing

    if not reminder_repo.update_columns(db, user_id, reminder_id, patch):
        raise ApiError.not_found("Reminder not found.")
    return find_by_id(db, user_id, reminder_id)


def remove(db: Session, user_id: int, reminder_id: int) -> None:
    if not reminder_repo.delete(db, user_id, reminder_id):
        raise ApiError.not_found("Reminder not found.")
