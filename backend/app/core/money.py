"""Money helpers.

PostgreSQL NUMERIC arrives as a `Decimal`, and every calculation in this app is
done in `Decimal` — never in binary floating point. The one place a float
appears is `to_amount`, at the JSON boundary, so the frontend keeps receiving
plain numbers ("30", "0.3") exactly as it did from the Express backend.

That final conversion is exact: two-decimal values below 10^8 are representable
in a double without loss, so no artefact like "300.00000000000006" can reach
the browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTS = Decimal("0.01")
MAX_AMOUNT = Decimal("99999999.99")


def to_decimal(value: object) -> Decimal:
    """DB value / literal -> Decimal, without ever passing through a float."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)
    if isinstance(value, float):
        # repr() gives the shortest round-tripping form, matching how
        # JavaScript stringifies the same number.
        return Decimal(repr(value))
    return Decimal(str(value).strip())


def quantize(value: object) -> Decimal:
    """Rounds to cents, half-up — the rounding a till uses."""
    try:
        return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, ArithmeticError):
        return Decimal("0.00")


def to_amount(value: object) -> float:
    """Turns a NUMERIC / number / None into a cents-rounded JSON number."""
    return float(quantize(value))


def format_rand(value: Decimal | float) -> str:
    """R-amount as it appears inside user-facing messages: 200.00"""
    return f"{quantize(value):.2f}"


@dataclass(frozen=True)
class ParsedAmount:
    ok: bool
    value: Decimal | None = None
    message: str | None = None


def parse_amount(
    value: object,
    field: str = "Amount",
    max_value: Decimal = MAX_AMOUNT,
) -> ParsedAmount:
    """Validates a user-supplied money amount.

    Returns ParsedAmount(ok=True, value=Decimal) or ParsedAmount(ok=False, message=…).
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return ParsedAmount(False, message=f"{field} is required.")
    if isinstance(value, bool) or isinstance(value, (list, dict)):
        return ParsedAmount(False, message=f"{field} must be a number.")

    try:
        number = to_decimal(value)
    except (InvalidOperation, ValueError, ArithmeticError):
        return ParsedAmount(False, message=f"{field} must be a number.")

    if not number.is_finite():
        return ParsedAmount(False, message=f"{field} must be a number.")
    if number <= 0:
        return ParsedAmount(False, message=f"{field} must be greater than zero.")
    if number > max_value:
        return ParsedAmount(False, message=f"{field} is too large.")

    # Reject more than two decimal places rather than silently rounding the
    # owner's money to something they did not type.
    rounded = number.quantize(CENTS, rounding=ROUND_HALF_UP)
    if number != rounded:
        return ParsedAmount(False, message=f"{field} cannot have more than two decimal places.")

    return ParsedAmount(True, value=rounded)
