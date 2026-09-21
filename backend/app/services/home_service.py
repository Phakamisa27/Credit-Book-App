"""The ThathaCash Home screen — everything it shows, in one request.

Same idea as report_service.dashboard(): one round trip on a slow phone
connection instead of four.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import cash_service, item_service, shop_rules

STOCK_PREVIEW = 5
RECENT_ENTRIES = 5


def home(db: Session, user_id: int) -> dict[str, Any]:
    cash = cash_service.cash_summary(db, user_id)
    order = item_service.suggested_order(
        db, user_id, cash_service.available_for_stock(db, user_id)
    )

    products = item_service.list_items(db, user_id)
    # Running-low products first — they are the reason to look at this list.
    products.sort(key=lambda p: (p["status"] != shop_rules.LOW, p["name"].lower()))
    low_count = sum(1 for p in products if p["status"] == shop_rules.LOW)

    recent = cash_service.list_entries(db, user_id, limit=RECENT_ENTRIES)["entries"]

    return {
        "cash": cash,
        "order": {
            "total": order["total"],
            "itemCount": len(order["items"]),
            "withinBudget": order["withinBudget"],
        },
        "stock": {
            "items": products[:STOCK_PREVIEW],
            "lowCount": low_count,
            "totalCount": len(products),
        },
        "recentEntries": recent,
    }
