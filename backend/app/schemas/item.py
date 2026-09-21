from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class ItemCreateRequest(RequestModel):
    """`name` and `price` are required. The stock fields are optional, so the
    Credit Book's original {name, price} body still works."""

    name: Any = None
    price: Any = None
    quantity: Any = None
    lowStockLevel: Any = None
    reorderQuantity: Any = None


class ItemUpdateRequest(RequestModel):
    """Every field optional; only the keys sent are changed."""

    name: Any = None
    price: Any = None
    quantity: Any = None
    lowStockLevel: Any = None
    reorderQuantity: Any = None
