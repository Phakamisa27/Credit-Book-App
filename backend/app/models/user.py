from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """The shop owner. This app has one owner, so the business profile lives here."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_check"),
        CheckConstraint("position('@' IN email) > 1", name="users_email_check"),
        CheckConstraint(
            "restock_reserve IS NULL OR restock_reserve >= 0", name="users_restock_reserve_check"
        ),
        CheckConstraint(
            "buffer_percent >= 0 AND buffer_percent <= 100", name="users_buffer_percent_check"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    business_name: Mapped[str | None] = mapped_column(Text)
    business_phone: Mapped[str | None] = mapped_column(Text)
    profile_image: Mapped[str | None] = mapped_column(Text)
    # Safe to draw settings. restock_reserve is NULL until the owner sets it.
    restock_reserve: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    buffer_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="10"
    )
    cash_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customers = relationship("Customer", back_populates="user", cascade="all, delete-orphan")
