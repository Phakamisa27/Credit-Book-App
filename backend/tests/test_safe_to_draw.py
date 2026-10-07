"""Safe to draw: the rule itself, the owner's settings, and cash recounts.

The rule tests call shop_rules directly — no database. The API tests share one
fresh account and run in order, each building on the one before.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services import shop_rules
from tests.conftest import Api

D = Decimal


# ---------------------------------------------------------------- the rule --
def test_the_example_from_the_brief() -> None:
    # Cash R250, keep R100 for restocking, 10% buffer (R25) -> R125.
    assert shop_rules.calculate_safe_to_draw(D(250), D(100), D(25)) == D("125.00")


def test_safe_to_draw_is_never_negative() -> None:
    assert shop_rules.calculate_safe_to_draw(D(100), D(100), D(10)) == D("0.00")
    assert shop_rules.calculate_safe_to_draw(D(-50), D(0), D(0)) == D("0.00")


def test_cents_the_owner_entered_are_kept() -> None:
    assert shop_rules.calculate_safe_to_draw(D("250.50"), D(100), D(26)) == D("124.50")


@pytest.mark.parametrize(
    "spend, days, owner, expected",
    [
        (D(700), 3, None, (D(100), "AVERAGE")),  # 700 / 7 days
        (D(1000), 5, D(50), (D(143), "AVERAGE")),  # 142.86 rounds UP to keep enough
        (D(700), 2, D(300), (D(300), "OWNER")),  # too few stock days -> owner's amount
        (D(0), 0, None, (D(0), "OWNER")),  # nothing set yet -> R0
    ],
)
def test_restock_reserve(spend, days, owner, expected) -> None:
    assert shop_rules.restock_reserve(spend, days, owner) == expected


def test_buffer_rounds_up_to_whole_rands_and_is_zero_without_cash() -> None:
    assert shop_rules.buffer_amount(D(250), D(10)) == D(25)
    assert shop_rules.buffer_amount(D(255), D(10)) == D(26)  # 25.50 -> 26
    assert shop_rules.buffer_amount(D(-100), D(10)) == D(0)


# --------------------------------------------------------------- the API ----
def summary(api: Api) -> dict:
    status, body = api.get("/cash/summary")
    assert status == 200
    return body["data"]


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def test_a_new_account_has_defaults_and_has_never_counted(api: Api) -> None:
    status, body = api.get("/auth/me")
    assert status == 200
    assert body["data"]["restockReserve"] is None
    assert body["data"]["bufferPercent"] == 10
    assert body["data"]["cashCountedAt"] is None

    data = summary(api)
    assert data["cashCountedAt"] is None
    assert data["safeToDraw"]["amount"] == 0
    assert data["drawsThisMonthCount"] == 0


def test_starting_cash_counts_as_counting(api: Api) -> None:
    api.post("/cash", {"type": "OPENING", "amount": 250})
    data = summary(api)
    assert data["cashCountedAt"] is not None

    # No stock history and no owner amount yet: keep R0, buffer 10%.
    std = data["safeToDraw"]
    assert std["restockSource"] == "OWNER"
    assert std["restockReserveSet"] is False
    assert std["restockReserve"] == 0
    assert std["buffer"] == 25
    assert std["amount"] == 225


def test_the_owners_restock_reserve_is_used_until_there_is_stock_history(api: Api) -> None:
    status, body = api.patch("/auth/me", {"restockReserve": 100})
    assert status == 200, body
    assert body["data"]["restockReserve"] == 100

    std = summary(api)["safeToDraw"]
    assert std["restockReserveSet"] is True
    assert std["restockReserve"] == 100
    assert std["amount"] == 125  # the brief's example: 250 - 100 - 25


def test_changing_the_buffer_changes_safe_to_draw_at_once(api: Api) -> None:
    status, body = api.patch("/auth/me", {"bufferPercent": 20})
    assert status == 200, body
    std = summary(api)["safeToDraw"]
    assert std["bufferPercent"] == 20
    assert std["buffer"] == 50
    assert std["amount"] == 100

    api.patch("/auth/me", {"bufferPercent": 10})


def test_three_days_of_stock_purchases_switch_to_the_average(api: Api) -> None:
    # Money in first, so there is cash to spend on stock.
    api.post("/cash", {"type": "INCOME", "amount": 1400})
    for n, amount in ((0, 300), (2, 200), (5, 200)):
        status, _ = api.post("/cash", {"type": "STOCK", "amount": amount, "date": days_ago(n)})
        assert status == 201

    # Too old to count: 7 days ago is outside "the last 7 days, today included".
    api.post("/cash", {"type": "STOCK", "amount": 999, "date": days_ago(7)})
    api.post("/cash", {"type": "INCOME", "amount": 999})

    data = summary(api)
    std = data["safeToDraw"]
    assert std["stockDays"] == 3
    assert std["restockSource"] == "AVERAGE"
    assert std["restockReserve"] == 100  # (300 + 200 + 200) / 7
    # cash = 250 + 1400 - 700 - 999 + 999 = 950; buffer 95
    assert data["cashAvailable"] == 950
    assert std["buffer"] == 95
    assert std["amount"] == 755


def test_draws_this_month_has_a_total_and_a_count(api: Api) -> None:
    api.post("/cash", {"type": "DRAW", "amount": 150, "note": "Groceries"})
    api.post("/cash", {"type": "DRAW", "amount": 50})
    data = summary(api)
    assert data["drawsThisMonth"] == 200
    assert data["drawsThisMonthCount"] == 2


def test_a_recount_makes_cash_match_the_till(api: Api) -> None:
    before = summary(api)
    assert before["cashAvailable"] == 750

    status, body = api.post("/cash/count", {"amount": 700})
    assert status == 200, body
    assert body["data"]["difference"] == -50
    assert body["data"]["cash"]["cashAvailable"] == 700
    assert body["data"]["cash"]["cashCountedAt"] >= before["cashCountedAt"]

    status, body = api.post("/cash/count", {"amount": 720.5})
    assert body["data"]["difference"] == 20.5
    assert body["data"]["cash"]["cashAvailable"] == 720.5


def test_a_matching_count_writes_no_entry_but_still_counts(api: Api) -> None:
    _, before = api.get("/cash?type=RECOUNT_IN")
    status, body = api.post("/cash/count", {"amount": 720.5})
    assert status == 200
    assert body["data"]["difference"] == 0
    _, after = api.get("/cash?type=RECOUNT_IN")
    assert len(after["data"]["entries"]) == len(before["data"]["entries"])


def test_recounts_are_listed_but_are_not_sales_or_expenses(api: Api) -> None:
    _, body = api.get("/cash")
    types = [e["type"] for e in body["data"]["entries"]]
    assert "RECOUNT_IN" in types and "RECOUNT_OUT" in types

    totals = body["data"]["totals"]
    assert totals["income"] == 1400 + 999
    assert totals["expenses"] == 0


def test_an_empty_till_is_a_real_count(api: Api) -> None:
    status, body = api.post("/cash/count", {"amount": 0})
    assert status == 200, body
    assert body["data"]["cash"]["cashAvailable"] == 0
    assert body["data"]["cash"]["safeToDraw"]["amount"] == 0


@pytest.mark.parametrize(
    "patch, message",
    [
        ({"restockReserve": -1}, "Restock reserve cannot be negative."),
        ({"restockReserve": "abc"}, "Restock reserve must be a number."),
        ({"bufferPercent": 101}, "Buffer must be a percentage from 0 to 100."),
        ({"bufferPercent": -5}, "Buffer must be a percentage from 0 to 100."),
        ({"bufferPercent": "ten"}, "Buffer must be a percentage from 0 to 100."),
    ],
)
def test_rejects_bad_settings(api: Api, patch: dict, message: str) -> None:
    status, body = api.patch("/auth/me", patch)
    assert status == 400
    assert body["message"] == message


def test_zero_is_a_valid_setting(api: Api) -> None:
    status, body = api.patch("/auth/me", {"restockReserve": 0, "bufferPercent": 0})
    assert status == 200, body
    assert body["data"]["restockReserve"] == 0
    assert body["data"]["bufferPercent"] == 0


def test_recounts_cannot_be_logged_by_hand(api: Api) -> None:
    status, _ = api.post("/cash", {"type": "RECOUNT_IN", "amount": 100})
    assert status == 400


def test_bad_counts_are_rejected(api: Api) -> None:
    assert api.post("/cash/count", {"amount": -10})[0] == 400
    assert api.post("/cash/count", {})[0] == 400
    assert api.post("/cash/count", {"amount": 10.555})[0] == 400


def test_counting_requires_login(anon: Api) -> None:
    assert anon.post("/cash/count", {"amount": 100})[0] == 401
