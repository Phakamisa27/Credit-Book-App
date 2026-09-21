"""Development seed data.

============================ DEVELOPMENT ONLY ============================
Creates a test account with a KNOWN password and fake customers so the app can
be clicked through immediately. Never run this against real books: it deletes
every customer, transaction, reminder and item belonging to the seed account
first.

    Login: owner@creditbook.test
    Pass:  Password123
==========================================================================

    python -m app.db.seed
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal

SEED_EMAIL = "owner@creditbook.test"
SEED_PASSWORD = "Password123"


def days_from_now(days: int) -> str:
    """Dates relative to today so "overdue" and "due soon" stay meaningful
    whenever the seed happens to be run."""
    return (date.today() + timedelta(days=days)).isoformat()


def days_ago_timestamp(days: int) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=days)


def money(value: float | str) -> Decimal:
    return Decimal(str(value))


# A transaction either carries `items` (a multi-item credit, where the total is
# computed from the lines) or a flat `amount` (a payment, or a single-line
# credit captured quickly).
CUSTOMERS: list[dict[str, Any]] = [
    {
        "fullName": "Thando Mkhize",
        "phone": "074 099 8882",
        "email": "thando@example.com",
        "address": "Umlazi, Section K",
        "gender": "female",
        "notes": "Buys groceries weekly. Pays every month-end.",
        "transactions": [
            {
                "type": "CREDIT",
                "dueDate": days_from_now(2),
                "daysAgo": 12,
                "items": [
                    {"name": "Bread", "quantity": 2, "unitPrice": money("15")},
                    {"name": "Milk 2L", "quantity": 3, "unitPrice": money("18")},
                    {"name": "Sugar 2.5kg", "quantity": 1, "unitPrice": money("64.99")},
                    {"name": "Cooking oil 750ml", "quantity": 1, "unitPrice": money("42.50")},
                ],
            },
            {"type": "PAYMENT", "amount": money("200"), "description": "Cash payment", "daysAgo": 8},
            {
                "type": "CREDIT",
                "dueDate": days_from_now(2),
                "daysAgo": 3,
                "items": [{"name": "Airtime R50", "quantity": 1, "unitPrice": money("50")}],
            },
        ],
    },
    {
        "fullName": "John Dlamini",
        "phone": "082 551 3390",
        "email": None,
        "address": "KwaMashu, Block H",
        "gender": "male",
        "notes": "Slow payer — follow up.",
        "transactions": [
            {"type": "CREDIT", "amount": money("800"), "description": "Building sand",
             "dueDate": days_from_now(-9), "daysAgo": 40},
            {"type": "CREDIT", "amount": money("300"), "description": "Cement bag",
             "dueDate": days_from_now(-9), "daysAgo": 35},
            {"type": "PAYMENT", "amount": money("300"), "description": "Cash payment",
             "daysAgo": 20},
        ],
    },
    {
        "fullName": "Nomsa Zulu",
        "phone": "073 224 7781",
        "email": "nomsa.zulu@example.com",
        "address": "Ntuzuma",
        "gender": "female",
        "notes": None,
        "transactions": [
            {"type": "CREDIT", "amount": money("1200"), "description": "School uniforms",
             "dueDate": days_from_now(-25), "daysAgo": 60},
            {"type": "PAYMENT", "amount": money("400"), "description": "EFT payment",
             "daysAgo": 45},
            {"type": "PAYMENT", "amount": money("100"), "description": "Cash payment",
             "daysAgo": 5},
        ],
    },
    {
        "fullName": "Sipho Ndlovu",
        "phone": "060 887 1204",
        "email": None,
        "address": "Inanda",
        "gender": "male",
        "notes": "Always settles in full.",
        "transactions": [
            {"type": "CREDIT", "amount": money("450"), "description": "Paraffin and candles",
             "dueDate": days_from_now(-14), "daysAgo": 30},
            {"type": "PAYMENT", "amount": money("450"), "description": "Cash payment",
             "daysAgo": 16},
        ],
    },
    {
        "fullName": "Precious Khumalo",
        "phone": "079 310 5567",
        "email": None,
        "address": "Umlazi, Section D",
        "gender": "female",
        "notes": "Runs a spaza shop.",
        "transactions": [
            {
                "type": "CREDIT",
                "dueDate": days_from_now(6),
                "daysAgo": 7,
                "items": [
                    {"name": "Cooldrink 2L crate", "quantity": 8, "unitPrice": money("220")},
                    {"name": "Bread", "quantity": 20, "unitPrice": money("15")},
                    {"name": "Maize meal 5kg", "quantity": 4, "unitPrice": money("79.99")},
                ],
            },
            {"type": "PAYMENT", "amount": money("900"), "description": "Cash payment",
             "daysAgo": 2},
        ],
    },
    {
        "fullName": "Bongani Cele",
        "phone": "083 442 9098",
        "email": None,
        "address": "Chatsworth",
        "gender": "male",
        "notes": None,
        "transactions": [
            {
                "type": "CREDIT",
                "dueDate": days_from_now(0),
                "daysAgo": 6,
                "items": [
                    {"name": "Bread", "quantity": 2, "unitPrice": money("15")},
                    {"name": "Milk 2L", "quantity": 1, "unitPrice": money("18")},
                ],
            },
        ],
    },
]

# ThathaCash stock. `price` is what the owner pays per unit; `low` is the
# running-low level and `reorder` how many they usually buy.
ITEMS = [
    {"name": "Coca-Cola 2L", "price": money("28"), "quantity": 5, "low": 6, "reorder": 12},
    {"name": "Bread", "price": money("16"), "quantity": 3, "low": 5, "reorder": 20},
    {"name": "Milk 1L", "price": money("18"), "quantity": 12, "low": 6, "reorder": 12},
    {"name": "Sunlight Soap", "price": money("14"), "quantity": 8, "low": 4, "reorder": 10},
    {"name": "Biscuits", "price": money("12"), "quantity": 6, "low": 5, "reorder": 12},
    {"name": "Cooking Oil 750ml", "price": money("38.50"), "quantity": 2, "low": 4, "reorder": 6},
    {"name": "Sugar 2kg", "price": money("42"), "quantity": 10, "low": 4, "reorder": 6},
    {"name": "Maize Meal 2kg", "price": money("30"), "quantity": 4, "low": 5, "reorder": 10},
]

# ThathaCash money in and out. Adds up to R4,200 cash available.
CASH_ENTRIES = [
    {"type": "OPENING", "amount": money("3000"), "note": "Cash in the till", "daysAgo": 9},
    {"type": "INCOME", "amount": money("1250"), "note": "Customer sales", "daysAgo": 6},
    {"type": "STOCK", "amount": money("1800"), "note": "Wholesaler", "daysAgo": 5},
    {"type": "INCOME", "amount": money("980"), "note": "Customer sales", "daysAgo": 4},
    {"type": "DRAW", "amount": money("200"), "note": "Personal", "daysAgo": 3},
    {"type": "EXPENSE", "amount": money("350"), "note": "Electricity", "daysAgo": 2},
    {"type": "INCOME", "amount": money("1450"), "note": "Customer sales", "daysAgo": 1},
    {"type": "DRAW", "amount": money("130"), "note": "Transport", "daysAgo": 0},
]


def seed() -> None:
    if settings.is_production:
        print("Refusing to seed: NODE_ENV is production.", file=sys.stderr)
        raise SystemExit(1)

    with SessionLocal() as session:
        # Upsert the seed owner so the id stays stable across re-seeds.
        user_id = session.execute(
            text(
                """
                INSERT INTO users (full_name, email, password_hash, business_name, business_phone)
                VALUES (:full_name, :email, :password_hash, :business_name, :business_phone)
                ON CONFLICT (email) DO UPDATE
                  SET password_hash = EXCLUDED.password_hash,
                      business_name = EXCLUDED.business_name,
                      updated_at    = now()
                RETURNING id
                """
            ),
            {
                "full_name": "Phakamani Sibisi",
                "email": SEED_EMAIL,
                "password_hash": hash_password(SEED_PASSWORD),
                "business_name": "Phaka's Spaza Shop",
                "business_phone": "074 099 8882",
            },
        ).scalar_one()

        # Clear this account's data only. Cascades handle transactions/reminders.
        session.execute(text("DELETE FROM customers WHERE user_id = :uid"), {"uid": user_id})
        session.execute(text("DELETE FROM items WHERE user_id = :uid"), {"uid": user_id})
        session.execute(text("DELETE FROM cash_entries WHERE user_id = :uid"), {"uid": user_id})

        for item in ITEMS:
            session.execute(
                text(
                    """
                    INSERT INTO items
                      (user_id, name, price, quantity, low_stock_level, reorder_quantity)
                    VALUES (:uid, :name, :price, :quantity, :low, :reorder)
                    """
                ),
                {"uid": user_id, **item},
            )

        for entry in CASH_ENTRIES:
            session.execute(
                text(
                    """
                    INSERT INTO cash_entries (user_id, type, amount, note, entry_date)
                    VALUES (:uid, :type, :amount, :note, :entry_date)
                    """
                ),
                {
                    "uid": user_id,
                    "type": entry["type"],
                    "amount": entry["amount"],
                    "note": entry["note"],
                    "entry_date": date.today() - timedelta(days=entry["daysAgo"]),
                },
            )

        transaction_count = 0
        item_count = 0

        for customer in CUSTOMERS:
            customer_id = session.execute(
                text(
                    """
                    INSERT INTO customers
                      (user_id, full_name, phone, email, address, gender, notes)
                    VALUES (:uid, :full_name, :phone, :email, :address, :gender, :notes)
                    RETURNING id
                    """
                ),
                {
                    "uid": user_id,
                    "full_name": customer["fullName"],
                    "phone": customer["phone"],
                    "email": customer["email"],
                    "address": customer["address"],
                    "gender": customer["gender"],
                    "notes": customer["notes"],
                },
            ).scalar_one()

            for transaction in customer["transactions"]:
                lines = transaction.get("items") or []

                # Same rule as the API: the total comes from the lines.
                if lines:
                    amount = sum(
                        (Decimal(line["quantity"]) * line["unitPrice"] for line in lines),
                        Decimal("0"),
                    )
                    description = ", ".join(
                        f"{line['name']} ×{line['quantity']}" if line["quantity"] > 1
                        else line["name"]
                        for line in lines
                    )
                else:
                    amount = transaction["amount"]
                    description = transaction["description"]

                transaction_id = session.execute(
                    text(
                        """
                        INSERT INTO transactions
                          (user_id, customer_id, type, amount, description, due_date, created_at)
                        VALUES (:uid, :cid, :type, :amount, :description, :due_date, :created_at)
                        RETURNING id
                        """
                    ),
                    {
                        "uid": user_id,
                        "cid": customer_id,
                        "type": transaction["type"],
                        "amount": amount,
                        "description": description,
                        "due_date": transaction.get("dueDate"),
                        "created_at": days_ago_timestamp(transaction["daysAgo"]),
                    },
                ).scalar_one()

                for position, line in enumerate(lines):
                    session.execute(
                        text(
                            """
                            INSERT INTO transaction_items
                              (transaction_id, name, quantity, unit_price, line_total, position)
                            VALUES (:tid, :name, :quantity, :unit_price, :line_total, :position)
                            """
                        ),
                        {
                            "tid": transaction_id,
                            "name": line["name"],
                            "quantity": line["quantity"],
                            "unit_price": line["unitPrice"],
                            "line_total": Decimal(line["quantity"]) * line["unitPrice"],
                            "position": position,
                        },
                    )
                    item_count += 1

                transaction_count += 1

            # A reminder for anyone still owing money.
            row = session.execute(
                text(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END), 0)
                        AS balance,
                      MIN(due_date) FILTER (WHERE type = 'CREDIT' AND due_date IS NOT NULL)
                        AS due_date
                    FROM transactions WHERE customer_id = :cid
                    """
                ),
                {"cid": customer_id},
            ).mappings().one()

            if row["balance"] > 0 and row["due_date"]:
                session.execute(
                    text(
                        """
                        INSERT INTO reminders
                          (user_id, customer_id, amount, due_date, status, notes)
                        VALUES (:uid, :cid, :amount, :due_date, 'PENDING', :notes)
                        """
                    ),
                    {
                        "uid": user_id,
                        "cid": customer_id,
                        "amount": row["balance"],
                        "due_date": row["due_date"],
                        "notes": "Follow up on outstanding balance.",
                    },
                )

        session.commit()

    print("Seed complete (DEVELOPMENT DATA).")
    print(f"  Customers    {len(CUSTOMERS)}")
    print(f"  Transactions {transaction_count}")
    print(f"  Line items   {item_count}")
    print(f"  Products     {len(ITEMS)}")
    print(f"  Cash entries {len(CASH_ENTRIES)}")
    print()
    print("  Test login — DEVELOPMENT ONLY")
    print(f"    Email    {SEED_EMAIL}")
    print(f"    Password {SEED_PASSWORD}")


if __name__ == "__main__":
    try:
        seed()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
