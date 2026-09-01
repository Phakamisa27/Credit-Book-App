"""Dashboard and reports.

Every figure is computed from the ledger. Nothing is cached and nothing is
summed in the browser, so the numbers the owner sees are the numbers in the
database — and the totals here reconcile with the customer balances that
produced them.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.money import to_amount
from app.core.serialize import date_only
from app.repositories import report_repo
from app.services import reminder_service, transaction_service


def totals(db: Session, user_id: int) -> dict[str, Any]:
    row = report_repo.balance_totals(db, user_id)
    ledger = report_repo.ledger_totals(db, user_id)

    return {
        "totalCustomers": int(row["total_customers"]),
        "totalOutstanding": to_amount(row["total_outstanding"]),
        "totalOverdue": to_amount(row["total_overdue"]),
        "customersOwing": int(row["customers_owing"]),
        "customersOverdue": int(row["customers_overdue"]),
        "customersDueToday": int(row["customers_due_today"]),
        "totalCreditIssued": to_amount(ledger["total_credit_issued"]),
        "totalPayments": to_amount(ledger["total_payments"]),
        "paidThisMonth": to_amount(ledger["paid_this_month"]),
        "creditThisMonth": to_amount(ledger["credit_this_month"]),
        "paidToday": to_amount(ledger["paid_today"]),
        "creditToday": to_amount(ledger["credit_today"]),
    }


def top_debtors(db: Session, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
    today = date.today()
    rows = report_repo.top_debtors(db, user_id, limit)

    return [
        {
            "id": row["id"],
            "fullName": row["full_name"],
            "phone": row["phone"],
            "balance": to_amount(row["balance"]),
            "dueDate": date_only(row["due_date"]) if row["due_date"] else None,
            "status": (
                "OVERDUE"
                if row["due_date"] and date.fromisoformat(date_only(row["due_date"])) < today
                else "OWING"
            ),
        }
        for row in rows
    ]


def overdue_customers(db: Session, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = report_repo.overdue_customers(db, user_id, limit)

    return [
        {
            "id": row["id"],
            "fullName": row["full_name"],
            "phone": row["phone"],
            "balance": to_amount(row["balance"]),
            "dueDate": date_only(row["due_date"]),
            "daysOverdue": int(row["days_overdue"]),
            "status": "OVERDUE",
        }
        for row in rows
    ]


def transactions_by_date(db: Session, user_id: int, days: int = 30) -> list[dict[str, Any]]:
    rows = report_repo.transactions_by_date(db, user_id, days)

    return [
        {
            "date": date_only(row["day"]),
            "credit": to_amount(row["credit"]),
            "payments": to_amount(row["payments"]),
            "count": int(row["count"]),
        }
        for row in rows
    ]


def dashboard(db: Session, user_id: int) -> dict[str, Any]:
    """Everything the dashboard needs, in one request."""
    reminders = reminder_service.list_reminders(db, user_id, status="OPEN")

    return {
        "summary": totals(db, user_id),
        "topDebtors": top_debtors(db, user_id, 5),
        "overdueCustomers": overdue_customers(db, user_id, 5),
        "recentTransactions": transaction_service.list_for_user(db, user_id, limit=8),
        "upcomingReminders": reminders[:5],
    }


def report(db: Session, user_id: int, days: int = 30) -> dict[str, Any]:
    """Everything the reports page needs."""
    return {
        "summary": totals(db, user_id),
        "topDebtors": top_debtors(db, user_id, 10),
        "overdueCustomers": overdue_customers(db, user_id, 20),
        "transactionsByDate": transactions_by_date(db, user_id, days),
    }
