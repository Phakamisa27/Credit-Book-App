"""Item (product / stock) SQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

COLUMNS = "id, name, price, quantity, low_stock_level, reorder_quantity, created_at"

UPDATABLE_COLUMNS = {
    "name": "name",
    "price": "price",
    "quantity": "quantity",
    "lowStockLevel": "low_stock_level",
    "reorderQuantity": "reorder_quantity",
}


def list_rows(db: Session, user_id: int) -> list[Any]:
    return (
        db.execute(
            text(f"SELECT {COLUMNS} FROM items WHERE user_id = :user_id ORDER BY name ASC"),
            {"user_id": user_id},
        )
        .mappings()
        .all()
    )


def find_row(db: Session, user_id: int, item_id: int) -> Any | None:
    return (
        db.execute(
            text(f"SELECT {COLUMNS} FROM items WHERE user_id = :user_id AND id = :id"),
            {"user_id": user_id, "id": item_id},
        )
        .mappings()
        .first()
    )


def running_low_rows(db: Session, user_id: int) -> list[Any]:
    """Products at or below their low-stock level, emptiest shelves first."""
    return (
        db.execute(
            text(
                f"""
                SELECT {COLUMNS} FROM items
                WHERE user_id = :user_id AND quantity <= low_stock_level
                ORDER BY quantity ASC, name ASC
                """
            ),
            {"user_id": user_id},
        )
        .mappings()
        .all()
    )


def insert(db: Session, user_id: int, data: dict[str, Any]) -> Any:
    row = (
        db.execute(
            text(
                f"""
                INSERT INTO items (user_id, name, price, quantity, low_stock_level, reorder_quantity)
                VALUES (:user_id, :name, :price, :quantity, :low_stock_level, :reorder_quantity)
                RETURNING {COLUMNS}
                """
            ),
            {
                "user_id": user_id,
                "name": data["name"],
                "price": data["price"],
                "quantity": data["quantity"],
                "low_stock_level": data["lowStockLevel"],
                "reorder_quantity": data["reorderQuantity"],
            },
        )
        .mappings()
        .first()
    )
    db.commit()
    return row


def update_columns(db: Session, user_id: int, item_id: int, patch: dict[str, Any]) -> Any | None:
    """Only the keys present in `patch` are written."""
    sets: list[str] = []
    params: dict[str, Any] = {"user_id": user_id, "id": item_id}

    for key, column in UPDATABLE_COLUMNS.items():
        if key in patch:
            params[column] = patch[key]
            sets.append(f"{column} = :{column}")

    if not sets:
        return find_row(db, user_id, item_id)

    row = (
        db.execute(
            text(
                f"UPDATE items SET {', '.join(sets)} "
                f"WHERE user_id = :user_id AND id = :id RETURNING {COLUMNS}"
            ),
            params,
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
