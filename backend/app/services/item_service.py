"""Quick-entry items — the owner's own product shortlist (Bread R18.50,
Airtime R30.00). Tapping one fills the record-credit form, which is the
difference between a 20-second capture and a 5-second one.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import to_amount
from app.core.serialize import iso_utc
from app.repositories import item_repo


def to_api(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "price": to_amount(row["price"]),
        "createdAt": iso_utc(row["created_at"]),
    }


def list_items(db: Session, user_id: int) -> list[dict[str, Any]]:
    return [to_api(row) for row in item_repo.list_rows(db, user_id)]


def create(db: Session, user_id: int, name: str, price: Decimal) -> dict[str, Any]:
    return to_api(item_repo.insert(db, user_id, name, price))


def remove(db: Session, user_id: int, item_id: int) -> None:
    if not item_repo.delete(db, user_id, item_id):
        raise ApiError.not_found("Item not found.")
