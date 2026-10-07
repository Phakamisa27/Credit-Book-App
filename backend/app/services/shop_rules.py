"""ThathaCash business rules — every number the owner sees is decided here.

Kept in one small file on purpose. During validation these rules WILL change
after talking to shop owners ("30% is too much", "bread runs low at 10, not
5"), and each one should be a one-line edit, not a hunt through the codebase.

    Cash available      = starting cash + income
                          - expenses - stock purchases - draws
                          (+/- any cash recount differences)

    Safe to draw        = cash available - kept for restocking - buffer,
                          never below zero
    Kept for restocking = average daily stock spend over the last 7 days,
                          or the owner's own amount while there are fewer
                          than 3 days of stock purchases to average
    Buffer              = the owner's buffer % of cash available (default 10%)

    Stock budget        = 70% of cash available (the Order screen's limit;
                          the other 30% is kept for expenses)

    Running low         = quantity at or below the product's low-stock level

    Suggested order     = every running-low product
                          x how many the owner usually orders
                          x the price the owner pays per unit
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_DOWN, Decimal

from app.core.money import quantize

# Share of cash kept aside for expenses and emergencies. The rest is what the
# owner can safely spend on stock.
RESERVE_SHARE = Decimal("0.30")

# Safe to draw.
RESTOCK_WINDOW_DAYS = 7  # average stock spend over this many days, today included
MIN_STOCK_DAYS = 3  # fewer days of stock purchases than this -> use the manual amount
DEFAULT_BUFFER_PERCENT = Decimal("10")

# Where "kept for restocking" came from, so the screen can say so.
RESTOCK_FROM_AVERAGE = "AVERAGE"
RESTOCK_FROM_OWNER = "OWNER"

LOW = "LOW"
GOOD = "GOOD"

ZERO = Decimal("0.00")


def _whole_rands_up(value: Decimal) -> Decimal:
    """Amounts we hold BACK round up, so we never suggest drawing too much."""
    return quantize(value.quantize(Decimal("1"), rounding=ROUND_CEILING))


def calculate_safe_to_draw(
    cash_available: Decimal, restock_reserve: Decimal, buffer: Decimal
) -> Decimal:
    """THE rule. What the owner can take without starving the shop.

    >>> calculate_safe_to_draw(Decimal(250), Decimal(100), Decimal(25))
    Decimal('125.00')
    """
    return quantize(max(ZERO, cash_available - restock_reserve - buffer))


def restock_reserve(
    stock_spend: Decimal, stock_days: int, owner_amount: Decimal | None
) -> tuple[Decimal, str]:
    """How much to keep for restocking, and where that number came from.

    `stock_spend` is everything paid for stock in the last RESTOCK_WINDOW_DAYS;
    `stock_days` is on how many different days stock was bought in that time.
    """
    if stock_days >= MIN_STOCK_DAYS:
        return _whole_rands_up(stock_spend / RESTOCK_WINDOW_DAYS), RESTOCK_FROM_AVERAGE
    return quantize(owner_amount or 0), RESTOCK_FROM_OWNER


def buffer_amount(cash_available: Decimal, buffer_percent: Decimal) -> Decimal:
    """The emergency buffer: a share of the cash there is. Nothing if none."""
    if cash_available <= 0:
        return ZERO
    return _whole_rands_up(cash_available * buffer_percent / 100)


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
