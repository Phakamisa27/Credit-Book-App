from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Customer(Base):
    """A person who buys on credit. Their balance is never stored — it is
    derived from the transaction ledger on every read."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="customers_full_name_check"),
        CheckConstraint("length(trim(phone)) > 0", name="customers_phone_check"),
        CheckConstraint("gender IN ('male', 'female')", name="customers_gender_check"),
        # One phone number per owner: stops the same person being captured twice.
        UniqueConstraint("user_id", "phone", name="customers_owner_phone_unique"),
        Index("customers_user_id_idx", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    gender: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="customers")
    transactions = relationship(
        "Transaction", back_populates="customer", cascade="all, delete-orphan"
    )
