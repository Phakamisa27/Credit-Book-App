from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Item(Base):
    """A product the shop sells.

    Originally the Credit Book's quick-entry list (e.g. Bread R18.50). In
    ThathaCash it is also the stock list: how many are on the shelf, when that
    counts as running low, and how many the owner usually orders. `price` is
    the price per unit the owner pays, used to estimate an order's cost.
    """

    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="items_name_check"),
        CheckConstraint("price > 0", name="items_price_check"),
        CheckConstraint("quantity >= 0", name="items_quantity_check"),
        CheckConstraint("low_stock_level >= 0", name="items_low_stock_level_check"),
        CheckConstraint("reorder_quantity >= 1", name="items_reorder_quantity_check"),
        UniqueConstraint("user_id", "name", name="items_owner_name_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Added in migration 0002 (ThathaCash stock).
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    low_stock_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    reorder_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
