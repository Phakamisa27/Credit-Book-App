from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Money coming IN to the shop's cash.
OPENING = "OPENING"  # the cash that was already in the shop on day one
INCOME = "INCOME"  # sales / takings

# Money going OUT of the shop's cash.
EXPENSE = "EXPENSE"  # electricity, rent, transport…
STOCK = "STOCK"  # buying stock from the wholesaler
DRAW = "DRAW"  # money the owner takes for themselves

# Written only by a cash recount, never logged directly: the difference
# between what the books say and what the owner counted in the till.
RECOUNT_IN = "RECOUNT_IN"  # the till had more than the books
RECOUNT_OUT = "RECOUNT_OUT"  # the till had less than the books

# What the owner can log through POST /api/cash.
CASH_TYPES = [OPENING, INCOME, EXPENSE, STOCK, DRAW]
ALL_CASH_TYPES = [*CASH_TYPES, RECOUNT_IN, RECOUNT_OUT]
MONEY_IN = [OPENING, INCOME, RECOUNT_IN]


class CashEntry(Base):
    """One movement of cash in or out of the shop (ThathaCash).

    Deliberately separate from `transactions`, which is the Credit Book's
    customer ledger. Cash available is never stored — it is derived from these
    rows on every read, the same way a customer's balance is.
    """

    __tablename__ = "cash_entries"
    __table_args__ = (
        CheckConstraint(
            "type IN ('OPENING', 'INCOME', 'EXPENSE', 'STOCK', 'DRAW', 'RECOUNT_IN', 'RECOUNT_OUT')",
            name="cash_entries_type_check",
        ),
        CheckConstraint("amount > 0", name="cash_entries_amount_check"),
        Index("cash_entries_user_date_idx", "user_id", "entry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    entry_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
