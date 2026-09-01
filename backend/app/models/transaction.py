from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CREDIT = "CREDIT"
PAYMENT = "PAYMENT"
TYPES = [CREDIT, PAYMENT]


class Transaction(Base):
    """The ledger. Append-only in normal use; deleting a row is allowed but
    always recalculates the balance because the balance is derived.

    `amount` is the grand total — for a multi-item credit it is the sum of the
    line items, computed server-side. Every balance and report query keeps
    aggregating this table alone and never has to know items exist.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('CREDIT', 'PAYMENT')", name="transactions_type_check"),
        CheckConstraint("amount > 0", name="transactions_amount_check"),
        CheckConstraint("length(trim(description)) > 0", name="transactions_description_check"),
        # Only credit can carry a due date; a payment is settled the moment it happens.
        CheckConstraint(
            "type = 'CREDIT' OR due_date IS NULL",
            name="transactions_due_date_only_on_credit",
        ),
        Index("transactions_customer_id_idx", "customer_id"),
        Index("transactions_user_id_created_idx", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    signature: Mapped[str | None] = mapped_column(Text)
    product_photo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customer = relationship("Customer", back_populates="transactions")
    items = relationship(
        "TransactionItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="TransactionItem.position, TransactionItem.id",
    )
