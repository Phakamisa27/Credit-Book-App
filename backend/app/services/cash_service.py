"""Cash in and out of the shop (ThathaCash).

Five kinds of entry, in words a shop owner uses:

    OPENING  Starting cash    — what was in the till on day one
    INCOME   Money in         — sales / takings
    EXPENSE  Expense          — electricity, rent, transport…
    STOCK    Stock purchase   — paying the wholesaler
    DRAW     Draw             — money the owner takes for themselves
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import quantize, to_amount
from app.core.serialize import date_only, iso_utc
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


def cash_summary(db: Session, user_id: int) -> dict[str, Any]:
    """The owner's cash position right now, shaped for the API."""
    row = cash_repo.cash_position(db, user_id)
    cash_available = quantize(row["cash_available"])
    split = shop_rules.split_cash(cash_available)

    return {
        "cashAvailable": to_amount(cash_available),
        "keptForExpenses": to_amount(split["keptForExpenses"]),
        "availableForStock": to_amount(split["availableForStock"]),
        "reservePercent": int(shop_rules.RESERVE_SHARE * 100),
        "drawsThisMonth": to_amount(row["draws_this_month"]),
        # False until the owner logs anything — the Home screen then asks for
        # their starting cash instead of showing a meaningless R0.00.
        "hasEntries": int(row["entry_count"]) > 0,
    }


def create(db: Session, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    return to_api(cash_repo.insert(db, user_id, data))


def remove(db: Session, user_id: int, entry_id: int) -> None:
    if not cash_repo.delete(db, user_id, entry_id):
        raise ApiError.not_found("Entry not found.")
