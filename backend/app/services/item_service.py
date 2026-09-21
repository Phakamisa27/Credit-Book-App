"""Products and stock.

Each item is one product the shop sells (Coca-Cola 2L, Bread…). The Credit
Book used them as quick-entry buttons; ThathaCash adds how many are on the
shelf, when that counts as running low, and how many to order.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import to_amount
from app.core.serialize import iso_utc
from app.repositories import item_repo
from app.services import shop_rules

DEFAULT_QUANTITY = 0
DEFAULT_LOW_STOCK_LEVEL = 5
DEFAULT_REORDER_QUANTITY = 10


def to_api(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    quantity = int(row["quantity"])
    low_stock_level = int(row["low_stock_level"])
    return {
        "id": row["id"],
        "name": row["name"],
        "price": to_amount(row["price"]),
        "quantity": quantity,
        "lowStockLevel": low_stock_level,
        "reorderQuantity": int(row["reorder_quantity"]),
        # Derived, never stored: changes the moment the quantity does.
        "status": shop_rules.stock_status(quantity, low_stock_level),
        "createdAt": iso_utc(row["created_at"]),
    }


def list_items(db: Session, user_id: int) -> list[dict[str, Any]]:
    return [to_api(row) for row in item_repo.list_rows(db, user_id)]


def create(db: Session, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Stock fields are optional, so the Credit Book's {name, price} request
    still works exactly as before."""
    return to_api(
        item_repo.insert(
            db,
            user_id,
            {
                "name": data["name"],
                "price": data["price"],
                "quantity": data.get("quantity", DEFAULT_QUANTITY),
                "lowStockLevel": data.get("lowStockLevel", DEFAULT_LOW_STOCK_LEVEL),
                "reorderQuantity": data.get("reorderQuantity", DEFAULT_REORDER_QUANTITY),
            },
        )
    )


def update(db: Session, user_id: int, item_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    row = item_repo.update_columns(db, user_id, item_id, patch)
    if row is None:
        raise ApiError.not_found("Product not found.")
    return to_api(row)


def remove(db: Session, user_id: int, item_id: int) -> None:
    if not item_repo.delete(db, user_id, item_id):
        raise ApiError.not_found("Item not found.")


def suggested_order(db: Session, user_id: int, available_for_stock: Decimal) -> dict[str, Any]:
    """What to buy next: every running-low product, in the owner's usual
    quantity, costed at the price they pay. Compared with the stock budget so
    the owner can see whether they can afford it — we warn, we don't trim."""
    lines: list[dict[str, Any]] = []
    total = Decimal("0.00")

    for row in item_repo.running_low_rows(db, user_id):
        order_quantity = int(row["reorder_quantity"])
        line_total = shop_rules.order_line_total(order_quantity, row["price"])
        total += line_total
        lines.append(
            {
                "id": row["id"],
                "name": row["name"],
                "inStock": int(row["quantity"]),
                "orderQuantity": order_quantity,
                "unitPrice": to_amount(row["price"]),
                "lineTotal": to_amount(line_total),
            }
        )

    return {
        "items": lines,
        "total": to_amount(total),
        "availableForStock": to_amount(available_for_stock),
        "withinBudget": total <= available_for_stock,
    }
