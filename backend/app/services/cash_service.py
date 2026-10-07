"""Cash in and out of the shop (ThathaCash).

Five kinds of entry, in words a shop owner uses:

    OPENING  Starting cash    — what was in the till on day one
    INCOME   Money in         — sales / takings
    EXPENSE  Expense          — electricity, rent, transport…
    STOCK    Stock purchase   — paying the wholesaler
    DRAW     Draw             — money the owner takes for themselves

plus two that only a till recount writes:

    RECOUNT_IN / RECOUNT_OUT  — the difference between the books and the till
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import quantize, to_amount
from app.core.serialize import date_only, iso_utc
from app.models.cash_entry import RECOUNT_IN, RECOUNT_OUT
from app.repositories import cash_repo
from app.services import shop_rules


def to_api(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "type": row["type"],
        "amount": to_amount(row["amount"]),
        "note": row["note"],
        "date": date_only(row["entry_date"]),
        "createdAt": iso_utc(row["created_at"]),
    }


def list_entries(
    db: Session,
    user_id: int,
    *,
    type_: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = cash_repo.DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Entries for the period (optionally one type), plus the period's totals.

    The totals always cover EVERY type in the period, even when the list is
    filtered to one — so the Income/Money-out cards don't jump around when the
    owner taps a filter chip.
    """
    rows = cash_repo.list_rows(
        db, user_id, type_=type_, date_from=date_from, date_to=date_to, limit=limit
    )
    sums = cash_repo.totals(db, user_id, date_from=date_from, date_to=date_to)

    expenses = quantize(sums["expenses"])
    stock = quantize(sums["stock"])
    draws = quantize(sums["draws"])

    return {
        "entries": [to_api(row) for row in rows],
        "totals": {
            "opening": to_amount(sums["opening"]),
            "income": to_amount(sums["income"]),
            "expenses": to_amount(expenses),
            "stock": to_amount(stock),
            "draws": to_amount(draws),
            "moneyOut": to_amount(expenses + stock + draws),
        },
    }


def available_for_stock(db: Session, user_id: int) -> Decimal:
    """The stock budget as a Decimal, for comparing against an order total."""
    row = cash_repo.cash_position(db, user_id)
    return shop_rules.split_cash(quantize(row["cash_available"]))["availableForStock"]


def safe_to_draw(db: Session, user_id: int, row: Any, cash_available: Decimal) -> dict[str, Any]:
    """Every line of the Safe to draw breakdown, so Home can show its working."""
    stock = cash_repo.stock_spend(db, user_id, shop_rules.RESTOCK_WINDOW_DAYS)
    owner_reserve = row["restock_reserve"]
    buffer_percent = quantize(
        shop_rules.DEFAULT_BUFFER_PERCENT if row["buffer_percent"] is None else row["buffer_percent"]
    )

    reserve, source = shop_rules.restock_reserve(
        quantize(stock["total"]), int(stock["days"]), owner_reserve
    )
    buffer = shop_rules.buffer_amount(cash_available, buffer_percent)

    return {
        "amount": to_amount(shop_rules.calculate_safe_to_draw(cash_available, reserve, buffer)),
        "restockReserve": to_amount(reserve),
        # AVERAGE: from the last 7 days of stock purchases. OWNER: the owner's
        # own amount, because there are too few stock days to average yet.
        "restockSource": source,
        "restockReserveSet": owner_reserve is not None,
        "stockDays": int(stock["days"]),
        "minStockDays": shop_rules.MIN_STOCK_DAYS,
        "buffer": to_amount(buffer),
        "bufferPercent": to_amount(buffer_percent),
    }


def cash_summary(db: Session, user_id: int) -> dict[str, Any]:
    """The owner's cash position right now, shaped for the API."""
    row = cash_repo.cash_position(db, user_id)
    cash_available = quantize(row["cash_available"])
    split = shop_rules.split_cash(cash_available)

    return {
        "cashAvailable": to_amount(cash_available),
        "safeToDraw": safe_to_draw(db, user_id, row, cash_available),
        # The Order screen's stock budget (70/30 split).
        "keptForExpenses": to_amount(split["keptForExpenses"]),
        "availableForStock": to_amount(split["availableForStock"]),
        "reservePercent": int(shop_rules.RESERVE_SHARE * 100),
        "drawsThisMonth": to_amount(row["draws_this_month"]),
        "drawsThisMonthCount": int(row["draws_this_month_count"]),
        # When the owner last confirmed the cash in the till. null = never.
        "cashCountedAt": iso_utc(row["cash_counted_at"]),
        # False until the owner logs anything — the Home screen then asks for
        # their starting cash instead of showing a meaningless R0.00.
        "hasEntries": int(row["entry_count"]) > 0,
    }


def record_count(db: Session, user_id: int, counted: Decimal) -> dict[str, Any]:
    """The owner counted the till. Makes cash available match it.

    The difference is saved as a RECOUNT_IN / RECOUNT_OUT entry rather than
    changing any past entry, so the history still adds up and sales and
    expense totals are not muddied by it.
    """
    row = cash_repo.cash_position(db, user_id)
    difference = counted - quantize(row["cash_available"])

    entry = None
    if difference != 0:
        entry = {
            "type": RECOUNT_IN if difference > 0 else RECOUNT_OUT,
            "amount": abs(difference),
            "note": "Cash recount",
            "date": None,  # today
        }
    cash_repo.record_count(db, user_id, entry)

    return {"difference": to_amount(difference), "cash": cash_summary(db, user_id)}


def create(db: Session, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    return to_api(cash_repo.insert(db, user_id, data))


def remove(db: Session, user_id: int, entry_id: int) -> None:
    if not cash_repo.delete(db, user_id, entry_id):
        raise ApiError.not_found("Entry not found.")
