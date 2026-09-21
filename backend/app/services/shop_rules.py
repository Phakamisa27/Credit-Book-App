"""ThathaCash business rules — every number the owner sees is decided here.

Kept in one small file on purpose. During validation these rules WILL change
after talking to shop owners ("30% is too much", "bread runs low at 10, not
5"), and each one should be a one-line edit, not a hunt through the codebase.

    Cash available      = starting cash + income
                          - expenses - stock purchases - draws

    Kept for expenses   = 30% of cash available
    Available for stock = the other 70%

    Running low         = quantity at or below the product's low-stock level

    Suggested order     = every running-low product
                          x how many the owner usually orders
                          x the price the owner pays per unit
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.core.money import quantize

# Share of cash kept aside for expenses and emergencies. The rest is what the
# owner can safely spend on stock.
RESERVE_SHARE = Decimal("0.30")

LOW = "LOW"
GOOD = "GOOD"


def split_cash(cash_available: Decimal) -> dict[str, Decimal]:
    """Splits cash into "kept for expenses" and "available for stock".

    If the books show no cash (or less than none — usually because starting
    cash was never entered) there is nothing to keep aside and nothing to
    spend, so both parts are zero rather than negative.
    """
    if cash_available <= 0:
        return {"keptForExpenses": Decimal("0.00"), "availableForStock": Decimal("0.00")}

    # Whole rands: "R3,000" is easier to act on than "R2,940.35". Rounding the
    # stock budget DOWN means we never suggest spending money that isn't there.
    available_for_stock = (cash_available * (1 - RESERVE_SHARE)).quantize(
        Decimal("1"), rounding=ROUND_DOWN
    )
    kept_for_expenses = quantize(cash_available - available_for_stock)
    return {
        "keptForExpenses": kept_for_expenses,
        "availableForStock": quantize(available_for_stock),
    }


def stock_status(quantity: int, low_stock_level: int) -> str:
    """LOW when the shelf is at or below the owner's own warning level."""
    return LOW if quantity <= low_stock_level else GOOD


def order_line_total(order_quantity: int, unit_price: Decimal) -> Decimal:
    """Whole units x a cents-exact price stays exact."""
    return quantize(Decimal(order_quantity) * unit_price)
