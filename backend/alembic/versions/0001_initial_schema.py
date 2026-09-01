"""Initial schema: the six tables defined by the original schema.sql.

(Kept ASCII-only: Alembic echoes this first line to the console, and a Windows
cp1252 terminal cannot print anything else.)

This revision reproduces the *existing* database exactly: same columns, same
types, same constraint names, same indexes. Nothing about the data model
changed in the migration from Node to Python.

An existing Credit Book database therefore does not need this revision applied.
Record it as already present instead:

    alembic stamp 0001

Only a brand-new database should run `alembic upgrade head`.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("business_name", sa.Text(), nullable=True),
        sa.Column("business_phone", sa.Text(), nullable=True),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="users_full_name_check"),
        sa.CheckConstraint("position('@' IN email) > 1", name="users_email_check"),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
    )

    # --------------------------------------------------------- customers ----
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="customers_full_name_check"),
        sa.CheckConstraint("length(trim(phone)) > 0", name="customers_phone_check"),
        sa.CheckConstraint("gender IN ('male', 'female')", name="customers_gender_check"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="customers_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="customers_pkey"),
        # One phone number per owner: stops the same person being captured twice.
        sa.UniqueConstraint("user_id", "phone", name="customers_owner_phone_unique"),
    )
    op.create_index("customers_user_id_idx", "customers", ["user_id"])

    # ------------------------------------------------------ transactions ----
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("product_photo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('CREDIT', 'PAYMENT')", name="transactions_type_check"),
        sa.CheckConstraint("amount > 0", name="transactions_amount_check"),
        sa.CheckConstraint(
            "length(trim(description)) > 0", name="transactions_description_check"
        ),
        # Only credit can carry a due date; a payment is settled the moment it happens.
        sa.CheckConstraint(
            "type = 'CREDIT' OR due_date IS NULL", name="transactions_due_date_only_on_credit"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="transactions_user_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="transactions_customer_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="transactions_pkey"),
    )
    op.create_index("transactions_customer_id_idx", "transactions", ["customer_id"])
    op.create_index(
        "transactions_user_id_created_idx",
        "transactions",
        ["user_id", sa.text("created_at DESC")],
    )

    # ------------------------------------------------- transaction_items ----
    op.create_table(
        "transaction_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="transaction_items_name_check"),
        sa.CheckConstraint("quantity > 0", name="transaction_items_quantity_check"),
        sa.CheckConstraint("unit_price > 0", name="transaction_items_unit_price_check"),
        sa.CheckConstraint("line_total > 0", name="transaction_items_line_total_check"),
        # The arithmetic is guaranteed by the database, not just by the API.
        sa.CheckConstraint(
            "line_total = quantity * unit_price", name="transaction_items_line_total_matches"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="transaction_items_transaction_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="transaction_items_pkey"),
    )
    op.create_index(
        "transaction_items_transaction_id_idx",
        "transaction_items",
        ["transaction_id", "position"],
    )

    # --------------------------------------------------------- reminders ----
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), server_default="PENDING", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="reminders_amount_check"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SENT', 'DONE', 'CANCELLED')", name="reminders_status_check"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="reminders_user_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="reminders_customer_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="reminders_pkey"),
    )
    op.create_index("reminders_user_due_idx", "reminders", ["user_id", "due_date"])

    # ------------------------------------------------------------- items ----
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="items_name_check"),
        sa.CheckConstraint("price > 0", name="items_price_check"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="items_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="items_pkey"),
        sa.UniqueConstraint("user_id", "name", name="items_owner_name_unique"),
    )


def downgrade() -> None:
    op.drop_table("items")
    op.drop_index("reminders_user_due_idx", table_name="reminders")
    op.drop_table("reminders")
    op.drop_index("transaction_items_transaction_id_idx", table_name="transaction_items")
    op.drop_table("transaction_items")
    op.drop_index("transactions_user_id_created_idx", table_name="transactions")
    op.drop_index("transactions_customer_id_idx", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("customers_user_id_idx", table_name="customers")
    op.drop_table("customers")
    op.drop_table("users")
