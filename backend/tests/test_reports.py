"""Reports and the dashboard — and that they reconcile with the ledger."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import Api


@pytest.fixture(scope="module", autouse=True)
def a_book_with_history(api: Api, new_customer) -> None:
    """A small but complete set of books: one settled customer, one owing, one
    overdue, plus a multi-item credit."""
    settled = new_customer("Reports Settled")
    api.post(
        f"/customers/{settled}/transactions",
        {"type": "CREDIT", "amount": 300, "description": "Groceries", "dueDate": "2030-01-01"},
    )
    api.post(
        f"/customers/{settled}/transactions",
        {"type": "PAYMENT", "amount": 300, "description": "Paid in full"},
    )

    owing = new_customer("Reports Owing")
    api.post(
        f"/customers/{owing}/transactions",
        {"type": "CREDIT", "amount": 500, "description": "Building sand", "dueDate": "2030-01-01"},
    )
    api.post(
        f"/customers/{owing}/transactions",
        {"type": "PAYMENT", "amount": 150, "description": "Part payment"},
    )

    overdue = new_customer("Reports Overdue")
    api.post(
        f"/customers/{overdue}/transactions",
        {
            "type": "CREDIT",
            "amount": 800,
            "description": "Late goods",
            "dueDate": (date.today() - timedelta(days=5)).isoformat(),
        },
    )

    multi = new_customer("Reports Multi")
    api.post(
        f"/customers/{multi}/transactions",
        {
            "type": "CREDIT",
            "dueDate": "2030-01-01",
            "items": [
                {"name": "Bread", "quantity": 2, "unitPrice": 15},
                {"name": "Perfume", "quantity": 1, "unitPrice": 120},
                {"name": "Milk", "quantity": 3, "unitPrice": 18},
                {"name": "Airtime", "quantity": 1, "unitPrice": 50},
            ],
        },
    )

    api.post("/reminders", {"customerId": owing, "amount": 350, "dueDate": "2030-01-01"})


def test_summary_totals_are_numbers_not_strings(api: Api) -> None:
    status, body = api.get("/reports/summary")
    assert status == 200
    assert isinstance(body["data"]["totalOutstanding"], (int, float))
    assert isinstance(body["data"]["totalCustomers"], int)
    assert body["data"]["totalOutstanding"] > 0


def test_credit_and_payment_totals(api: Api) -> None:
    _, body = api.get("/reports/summary")
    summary = body["data"]
    # 300 + 500 + 800 + 254 issued, 300 + 150 paid.
    assert summary["totalCreditIssued"] == 1854
    assert summary["totalPayments"] == 450
    assert summary["totalOutstanding"] == 1404


def test_outstanding_counts_only_customers_who_owe(api: Api) -> None:
    _, body = api.get("/reports/summary")
    summary = body["data"]
    assert summary["totalCustomers"] == 4
    assert summary["customersOwing"] == 3
    assert summary["customersOverdue"] == 1
    assert summary["totalOverdue"] == 800


def test_outstanding_total_matches_the_sum_of_positive_balances(api: Api) -> None:
    _, customers = api.get("/customers")
    expected = sum(c["balance"] for c in customers["data"] if c["balance"] > 0)

    _, summary = api.get("/reports/summary")
    assert round(summary["data"]["totalOutstanding"] * 100) == round(expected * 100)


def test_credit_issued_matches_the_sum_of_credit_transactions(api: Api) -> None:
    _, feed = api.get("/transactions?type=CREDIT")
    expected = sum(t["amount"] for t in feed["data"])

    _, summary = api.get("/reports/summary")
    assert round(summary["data"]["totalCreditIssued"] * 100) == round(expected * 100)


def test_payments_match_the_sum_of_payment_transactions(api: Api) -> None:
    _, feed = api.get("/transactions?type=PAYMENT")
    expected = sum(t["amount"] for t in feed["data"])

    _, summary = api.get("/reports/summary")
    assert round(summary["data"]["totalPayments"] * 100) == round(expected * 100)


def test_the_ledger_reconciles_credit_minus_payments_to_outstanding(api: Api) -> None:
    """Every customer here either owes money or is square, so the whole ledger
    nets exactly to the outstanding figure."""
    _, summary = api.get("/reports/summary")
    data = summary["data"]
    assert data["totalCreditIssued"] - data["totalPayments"] == data["totalOutstanding"]


def test_dashboard_returns_every_section(api: Api) -> None:
    status, body = api.get("/reports/dashboard")
    assert status == 200
    assert body["data"]["summary"]
    assert isinstance(body["data"]["topDebtors"], list)
    assert isinstance(body["data"]["overdueCustomers"], list)
    assert isinstance(body["data"]["recentTransactions"], list)
    assert isinstance(body["data"]["upcomingReminders"], list)


def test_top_debtors_are_ordered_by_balance(api: Api) -> None:
    _, body = api.get("/reports/dashboard")
    balances = [d["balance"] for d in body["data"]["topDebtors"]]
    assert balances == sorted(balances, reverse=True)
    assert balances[0] == 800


def test_overdue_customers_carry_their_days_overdue(api: Api) -> None:
    _, body = api.get("/reports/dashboard")
    overdue = body["data"]["overdueCustomers"]
    assert len(overdue) == 1
    assert overdue[0]["fullName"] == "Reports Overdue"
    assert overdue[0]["daysOverdue"] == 5
    assert overdue[0]["status"] == "OVERDUE"


def test_full_report_includes_daily_activity(api: Api) -> None:
    status, body = api.get("/reports?days=30")
    assert status == 200
    assert isinstance(body["data"]["transactionsByDate"], list)
    assert len(body["data"]["transactionsByDate"]) > 0

    today = body["data"]["transactionsByDate"][-1]
    assert today["credit"] > 0
    assert today["count"] > 0


def test_daily_activity_reconciles_with_the_summary(api: Api) -> None:
    _, body = api.get("/reports?days=365")
    daily = body["data"]["transactionsByDate"]

    assert round(sum(d["credit"] for d in daily) * 100) == round(
        body["data"]["summary"]["totalCreditIssued"] * 100
    )
    assert round(sum(d["payments"] for d in daily) * 100) == round(
        body["data"]["summary"]["totalPayments"] * 100
    )


def test_a_silly_days_value_is_clamped_rather_than_failing(api: Api) -> None:
    assert api.get("/reports?days=0")[0] == 200
    assert api.get("/reports?days=99999")[0] == 200
    assert api.get("/reports?days=abc")[0] == 200
