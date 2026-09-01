"""Dashboard and report SQL.

Every figure here is computed from the ledger in SQL. Nothing is cached and
nothing is summed in the browser, so the numbers the owner sees are the numbers
in the database. These statements are the Express backend's, unchanged.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Balance + earliest outstanding due date, per customer. The basis of almost
# every figure below.
BALANCES_CTE = """
  WITH customer_balances AS (
    SELECT
      c.id,
      c.full_name,
      c.phone,
      COALESCE(SUM(CASE WHEN t.type = 'CREDIT' THEN t.amount ELSE -t.amount END), 0) AS balance,
      MIN(t.due_date) FILTER (WHERE t.type = 'CREDIT' AND t.due_date IS NOT NULL) AS due_date
    FROM customers c
    LEFT JOIN transactions t ON t.customer_id = c.id
    WHERE c.user_id = :user_id
    GROUP BY c.id
  )
"""


def balance_totals(db: Session, user_id: int) -> Any:
    sql = f"""
    {BALANCES_CTE}
    SELECT
      (SELECT COUNT(*) FROM customers WHERE user_id = :user_id) AS total_customers,
      COALESCE(SUM(balance) FILTER (WHERE balance > 0), 0) AS total_outstanding,
      COALESCE(SUM(balance) FILTER (WHERE balance > 0 AND due_date < CURRENT_DATE), 0)
        AS total_overdue,
      COUNT(*) FILTER (WHERE balance > 0) AS customers_owing,
      COUNT(*) FILTER (WHERE balance > 0 AND due_date < CURRENT_DATE) AS customers_overdue,
      COUNT(*) FILTER (WHERE balance > 0 AND due_date = CURRENT_DATE) AS customers_due_today
    FROM customer_balances
    """
    return db.execute(text(sql), {"user_id": user_id}).mappings().first()


def ledger_totals(db: Session, user_id: int) -> Any:
    sql = """
    SELECT
      COALESCE(SUM(amount) FILTER (WHERE type = 'CREDIT'), 0) AS total_credit_issued,
      COALESCE(SUM(amount) FILTER (WHERE type = 'PAYMENT'), 0) AS total_payments,
      COALESCE(SUM(amount) FILTER (
        WHERE type = 'PAYMENT' AND created_at >= date_trunc('month', CURRENT_DATE)
      ), 0) AS paid_this_month,
      COALESCE(SUM(amount) FILTER (
        WHERE type = 'CREDIT' AND created_at >= date_trunc('month', CURRENT_DATE)
      ), 0) AS credit_this_month,
      COALESCE(SUM(amount) FILTER (
        WHERE type = 'PAYMENT' AND created_at >= CURRENT_DATE
      ), 0) AS paid_today,
      COALESCE(SUM(amount) FILTER (
        WHERE type = 'CREDIT' AND created_at >= CURRENT_DATE
      ), 0) AS credit_today
    FROM transactions
    WHERE user_id = :user_id
    """
    return db.execute(text(sql), {"user_id": user_id}).mappings().first()


def top_debtors(db: Session, user_id: int, limit: int = 5) -> list[Any]:
    """Customers with the largest outstanding balance."""
    sql = f"""
    {BALANCES_CTE}
    SELECT id, full_name, phone, balance, due_date
    FROM customer_balances
    WHERE balance > 0
    ORDER BY balance DESC, full_name ASC
    LIMIT :limit
    """
    return db.execute(text(sql), {"user_id": user_id, "limit": limit}).mappings().all()


def overdue_customers(db: Session, user_id: int, limit: int = 20) -> list[Any]:
    """Customers who owe money past their due date, most overdue first."""
    sql = f"""
    {BALANCES_CTE}
    SELECT id, full_name, phone, balance, due_date,
           (CURRENT_DATE - due_date) AS days_overdue
    FROM customer_balances
    WHERE balance > 0 AND due_date < CURRENT_DATE
    ORDER BY due_date ASC, balance DESC
    LIMIT :limit
    """
    return db.execute(text(sql), {"user_id": user_id, "limit": limit}).mappings().all()


def transactions_by_date(db: Session, user_id: int, days: int = 30) -> list[Any]:
    """Credit vs payments per day, for the reports page."""
    sql = """
    SELECT
      created_at::date AS day,
      COALESCE(SUM(amount) FILTER (WHERE type = 'CREDIT'), 0)  AS credit,
      COALESCE(SUM(amount) FILTER (WHERE type = 'PAYMENT'), 0) AS payments,
      COUNT(*) AS count
    FROM transactions
    WHERE user_id = :user_id
      AND created_at >= CURRENT_DATE - (CAST(:days AS int) - 1)
    GROUP BY day
    ORDER BY day ASC
    """
    return db.execute(text(sql), {"user_id": user_id, "days": days}).mappings().all()
