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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

STATUSES = ["PENDING", "SENT", "DONE", "CANCELLED"]


class Reminder(Base):
    """A note-to-self with a due date. No scheduler, no email queue — the owner
    opens the reminders page, sees who to chase, and sends a message by hand."""

    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="reminders_amount_check"),
        CheckConstraint(
            "status IN ('PENDING', 'SENT', 'DONE', 'CANCELLED')", name="reminders_status_check"
        ),
        Index("reminders_user_due_idx", "user_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="PENDING", default="PENDING"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
