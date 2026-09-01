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
    """Owner-defined quick-entry products (e.g. Bread R18.50) used by the
    record-credit screen. Every shop stocks different things."""

    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="items_name_check"),
        CheckConstraint("price > 0", name="items_price_check"),
        UniqueConstraint("user_id", "name", name="items_owner_name_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
