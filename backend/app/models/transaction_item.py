from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionItem(Base):
    """Line items for a credit transaction. One customer taking bread, milk and
    airtime in a single visit is ONE transaction with three item rows — not
    three transactions.

    Quantity is an INTEGER. Whole units keep `line_total = quantity *
    unit_price` exact to the cent, with no rounding to argue about later. To
    sell 1.5kg, enter quantity 1 with the unit price for that weight.
    """

    __tablename__ = "transaction_items"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="transaction_items_name_check"),
        CheckConstraint("quantity > 0", name="transaction_items_quantity_check"),
        CheckConstraint("unit_price > 0", name="transaction_items_unit_price_check"),
        CheckConstraint("line_total > 0", name="transaction_items_line_total_check"),
        # The arithmetic is guaranteed by the database, not just by the API.
        CheckConstraint(
            "line_total = quantity * unit_price",
            name="transaction_items_line_total_matches",
        ),
        Index("transaction_items_transaction_id_idx", "transaction_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    transaction = relationship("Transaction", back_populates="items")
