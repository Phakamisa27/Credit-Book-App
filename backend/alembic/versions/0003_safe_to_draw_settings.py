"""Safe to draw: owner settings, cash recounts.

(Kept ASCII-only: Alembic echoes this first line to the console, and a Windows
cp1252 terminal cannot print anything else.)

Purely ADDITIVE. No row is removed or changed except to fill the new
cash_counted_at column, and every existing entry type is still allowed.

  users         + restock_reserve    manual "keep for restocking" amount, used
                                     until there are 3 days of stock purchases.
                                     NULL = the owner has not set it yet.
                + buffer_percent     emergency buffer, % of cash (default 10)
                + cash_counted_at    when the owner last confirmed the cash

  cash_entries  type may also be RECOUNT_IN / RECOUNT_OUT: the difference
                between the books and a till count, so cash available matches
                the till without pretending the difference was a sale or an
                expense.

Existing owners get cash_counted_at = when they logged their starting cash.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TYPES = "type IN ('OPENING', 'INCOME', 'EXPENSE', 'STOCK', 'DRAW')"
NEW_TYPES = "type IN ('OPENING', 'INCOME', 'EXPENSE', 'STOCK', 'DRAW', 'RECOUNT_IN', 'RECOUNT_OUT')"


def upgrade() -> None:
    # ------------------------------------------------------ users: settings --
    op.add_column("users", sa.Column("restock_reserve", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "users",
        sa.Column("buffer_percent", sa.Numeric(5, 2), server_default="10", nullable=False),
    )
    op.add_column("users", sa.Column("cash_counted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "users_restock_reserve_check", "users", "restock_reserve IS NULL OR restock_reserve >= 0"
    )
    op.create_check_constraint(
        "users_buffer_percent_check", "users", "buffer_percent >= 0 AND buffer_percent <= 100"
    )

    # Starting cash was the owner's first count.
    op.execute(
        """
        UPDATE users u
        SET cash_counted_at = o.counted_at
        FROM (
          SELECT user_id, MAX(created_at) AS counted_at
          FROM cash_entries WHERE type = 'OPENING'
          GROUP BY user_id
        ) o
        WHERE o.user_id = u.id
        """
    )

    # --------------------------------------------- cash_entries: recounts ----
    op.drop_constraint("cash_entries_type_check", "cash_entries", type_="check")
    op.create_check_constraint("cash_entries_type_check", "cash_entries", NEW_TYPES)


def downgrade() -> None:
    op.execute("DELETE FROM cash_entries WHERE type IN ('RECOUNT_IN', 'RECOUNT_OUT')")
    op.drop_constraint("cash_entries_type_check", "cash_entries", type_="check")
    op.create_check_constraint("cash_entries_type_check", "cash_entries", OLD_TYPES)

    op.drop_constraint("users_buffer_percent_check", "users", type_="check")
    op.drop_constraint("users_restock_reserve_check", "users", type_="check")
    op.drop_column("users", "cash_counted_at")
    op.drop_column("users", "buffer_percent")
    op.drop_column("users", "restock_reserve")
