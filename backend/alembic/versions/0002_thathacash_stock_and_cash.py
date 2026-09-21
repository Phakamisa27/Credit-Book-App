"""ThathaCash: stock counts on items, and a cash_entries table.

(Kept ASCII-only: Alembic echoes this first line to the console, and a Windows
cp1252 terminal cannot print anything else.)

Purely ADDITIVE. No existing table, column, constraint or row is removed or
changed, so every Credit Book record survives and the credit API keeps working.

  items         + quantity           how many are in the shop right now
                + low_stock_level    "running low" at or below this number
                + reorder_quantity   how many the owner usually buys

  cash_entries  new table: money in and money out of the shop
                (starting cash, income, expenses, stock purchases, draws)

Existing items get the defaults (0 in stock, low at 5, order 10), which the
owner then corrects on the Stock screen.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------- items: stock ----
    # server_default fills every existing row, so NOT NULL is safe to add.
    op.add_column("items", sa.Column("quantity", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "items", sa.Column("low_stock_level", sa.Integer(), server_default="5", nullable=False)
    )
    op.add_column(
        "items", sa.Column("reorder_quantity", sa.Integer(), server_default="10", nullable=False)
    )
    op.create_check_constraint("items_quantity_check", "items", "quantity >= 0")
    op.create_check_constraint("items_low_stock_level_check", "items", "low_stock_level >= 0")
    op.create_check_constraint("items_reorder_quantity_check", "items", "reorder_quantity >= 1")

    # ------------------------------------------------------- cash_entries ----
    op.create_table(
        "cash_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        # The day the money moved. Separate from created_at so yesterday's
        # takings can be logged this morning.
        sa.Column("entry_date", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "type IN ('OPENING', 'INCOME', 'EXPENSE', 'STOCK', 'DRAW')",
            name="cash_entries_type_check",
        ),
        sa.CheckConstraint("amount > 0", name="cash_entries_amount_check"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="cash_entries_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="cash_entries_pkey"),
    )
    op.create_index("cash_entries_user_date_idx", "cash_entries", ["user_id", "entry_date"])


def downgrade() -> None:
    op.drop_index("cash_entries_user_date_idx", table_name="cash_entries")
    op.drop_table("cash_entries")
    op.drop_constraint("items_reorder_quantity_check", "items", type_="check")
    op.drop_constraint("items_low_stock_level_check", "items", type_="check")
    op.drop_constraint("items_quantity_check", "items", type_="check")
    op.drop_column("items", "reorder_quantity")
    op.drop_column("items", "low_stock_level")
    op.drop_column("items", "quantity")
