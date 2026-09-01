"""Quick-entry item SQL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_rows(db: Session, user_id: int) -> list[Any]:
    return (
        db.execute(
            text(
                "SELECT id, name, price, created_at FROM items "
                "WHERE user_id = :user_id ORDER BY name ASC"
            ),
            {"user_id": user_id},
        )
        .mappings()
        .all()
    )


def insert(db: Session, user_id: int, name: str, price: Decimal) -> Any:
    row = (
        db.execute(
            text(
                "INSERT INTO items (user_id, name, price) VALUES (:user_id, :name, :price) "
                "RETURNING id, name, price, created_at"
            ),
            {"user_id": user_id, "name": name, "price": price},
        )
        .mappings()
        .first()
    )
    db.commit()
    return row


def delete(db: Session, user_id: int, item_id: int) -> bool:
    row = db.execute(
        text("DELETE FROM items WHERE user_id = :user_id AND id = :id RETURNING id"),
        {"user_id": user_id, "id": item_id},
    ).first()
    db.commit()
    return row is not None
