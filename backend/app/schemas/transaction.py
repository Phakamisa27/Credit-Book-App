from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class TransactionCreateRequest(RequestModel):
    """Two shapes are accepted:

        {"type": "CREDIT", "items": [{"name", "quantity", "unitPrice"}, …], "dueDate"}
        {"type": "CREDIT" | "PAYMENT", "amount", "description", "dueDate"}

    With `items`, the server computes the grand total. Any `amount` sent
    alongside is ignored rather than trusted.
    """

    type: Any = None
    items: Any = None
    amount: Any = None
    description: Any = None
    dueDate: Any = None
    notes: Any = None
    signature: Any = None
    productPhoto: Any = None
