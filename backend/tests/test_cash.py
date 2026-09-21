"""ThathaCash cash entries: money in, expenses, stock purchases and draws.

The whole module shares one fresh account, so the tests run in order and each
builds on the entries logged before it.
"""

from __future__ import annotations

from datetime import date

import pytest

from tests.conftest import TEST_PASSWORD, Api, delete_account, unique_email

STATE: dict[str, int] = {}


def summary(api: Api) -> dict:
    status, body = api.get("/cash/summary")
    assert status == 200
    return body["data"]


def test_a_new_account_has_no_cash_and_no_entries(api: Api) -> None:
    data = summary(api)
    assert data["cashAvailable"] == 0
    assert data["availableForStock"] == 0
    assert data["keptForExpenses"] == 0
    assert data["hasEntries"] is False


def test_logs_starting_cash(api: Api) -> None:
    status, body = api.post(
        "/cash", {"type": "OPENING", "amount": 3000, "note": "Cash in the till", "date": "2026-09-01"}
    )
    assert status == 201
    entry = body["data"]
    assert entry["type"] == "OPENING"
    assert entry["amount"] == 3000
    assert entry["note"] == "Cash in the till"
    assert entry["date"] == "2026-09-01"


def test_logs_money_in_expenses_stock_and_a_draw(api: Api) -> None:
    entries = [
        {"type": "INCOME", "amount": 1250, "note": "Customer sales", "date": "2026-09-02"},
        {"type": "INCOME", "amount": 2430, "note": "Customer sales", "date": "2026-09-10"},
        {"type": "EXPENSE", "amount": 350, "note": "Electricity", "date": "2026-09-03"},
        {"type": "STOCK", "amount": 1800, "note": "Wholesaler", "date": "2026-09-04"},
        {"type": "DRAW", "amount": 200, "note": "Personal", "date": "2026-09-05"},
    ]
    for entry in entries:
        status, body = api.post("/cash", entry)
        assert status == 201, body
    STATE["draw"] = body["data"]["id"]


def test_cash_available_is_money_in_minus_money_out(api: Api) -> None:
    # (3000 + 1250 + 2430) - (350 + 1800 + 200) = 4330
    data = summary(api)
    assert data["cashAvailable"] == 4330
    assert data["hasEntries"] is True


def test_seventy_percent_is_available_for_stock_in_whole_rands(api: Api) -> None:
    # 70% of 4330 = 3031, kept aside = the remaining 1299.
    data = summary(api)
    assert data["reservePercent"] == 30
    assert data["availableForStock"] == 3031
    assert data["keptForExpenses"] == 1299
    assert data["availableForStock"] + data["keptForExpenses"] == data["cashAvailable"]


def test_date_defaults_to_today(api: Api) -> None:
    status, body = api.post("/cash", {"type": "DRAW", "amount": 150})
    assert status == 201
    assert body["data"]["date"] == date.today().isoformat()
    assert body["data"]["note"] is None
    STATE["draw_today"] = body["data"]["id"]


def test_draws_this_month_counts_only_this_months_draws(api: Api) -> None:
    # The R200 draw is dated 2026-09-05; only the R150 one is certainly "this month".
    data = summary(api)
    today = date.today()
    expected = 150 + (200 if (today.year, today.month) == (2026, 9) else 0)
    assert data["drawsThisMonth"] == expected


def test_lists_entries_newest_first_with_totals(api: Api) -> None:
    status, body = api.get("/cash?from=2026-09-01&to=2026-09-30")
    assert status == 200
    dates = [e["date"] for e in body["data"]["entries"]]
    assert dates == sorted(dates, reverse=True)

    totals = body["data"]["totals"]
    assert totals["opening"] == 3000
    assert totals["income"] == 3680
    assert totals["expenses"] == 350
    assert totals["stock"] == 1800
    assert totals["draws"] >= 200
    assert totals["moneyOut"] == totals["expenses"] + totals["stock"] + totals["draws"]


def test_the_period_filter_is_inclusive(api: Api) -> None:
    _, body = api.get("/cash?from=2026-09-02&to=2026-09-04")
    types = sorted(e["type"] for e in body["data"]["entries"])
    assert types == ["EXPENSE", "INCOME", "STOCK"]
    assert body["data"]["totals"]["income"] == 1250
    assert body["data"]["totals"]["opening"] == 0


def test_the_type_filter_narrows_the_list_but_not_the_totals(api: Api) -> None:
    _, body = api.get("/cash?type=INCOME&from=2026-09-01&to=2026-09-30")
    assert {e["type"] for e in body["data"]["entries"]} == {"INCOME"}
    # Totals still describe the whole period.
    assert body["data"]["totals"]["expenses"] == 350


@pytest.mark.parametrize(
    "entry, message",
    [
        ({"type": "LOAN", "amount": 100}, "Type must be one of: OPENING, INCOME, EXPENSE, STOCK, DRAW."),
        ({"amount": 100}, "Type must be one of: OPENING, INCOME, EXPENSE, STOCK, DRAW."),
        ({"type": "DRAW", "amount": 0}, "Amount must be greater than zero."),
        ({"type": "DRAW", "amount": -50}, "Amount must be greater than zero."),
        ({"type": "DRAW"}, "Amount is required."),
        ({"type": "DRAW", "amount": 10.555}, "Amount cannot have more than two decimal places."),
        ({"type": "DRAW", "amount": 10, "date": "17/09/2026"}, "Date must be in YYYY-MM-DD format."),
        ({"type": "DRAW", "amount": 10, "date": "2026-02-30"}, "Date is not a real date."),
    ],
)
def test_rejects_invalid_entries(api: Api, entry: dict, message: str) -> None:
    status, body = api.post("/cash", entry)
    assert status == 400
    assert body["message"] == message


def test_rejects_a_bad_filter(api: Api) -> None:
    assert api.get("/cash?type=LOAN")[0] == 400
    assert api.get("/cash?from=yesterday")[0] == 400


def test_deleting_an_entry_puts_the_cash_back(api: Api) -> None:
    before = summary(api)["cashAvailable"]
    status, _ = api.delete(f"/cash/{STATE['draw']}")
    assert status == 200
    assert summary(api)["cashAvailable"] == before + 200


def test_deleting_an_unknown_entry_404s(api: Api) -> None:
    assert api.delete("/cash/99999999")[0] == 404


def test_more_money_out_than_in_gives_no_stock_budget(api: Api) -> None:
    api.post("/cash", {"type": "EXPENSE", "amount": 10000, "note": "Big repair"})
    data = summary(api)
    assert data["cashAvailable"] < 0
    assert data["availableForStock"] == 0
    assert data["keptForExpenses"] == 0


def test_another_account_cannot_see_or_delete_our_entries(client, api: Api) -> None:
    email = unique_email("cash-other")
    status, body = Api(client).post(
        "/auth/register",
        {"fullName": "Other Owner", "email": email, "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 201
    other = Api(client, body["data"]["token"])
    try:
        assert other.get("/cash")[1]["data"]["entries"] == []
        assert other.get("/cash/summary")[1]["data"]["cashAvailable"] == 0
        assert other.delete(f"/cash/{STATE['draw_today']}")[0] == 404
    finally:
        delete_account(email)

    _, ours = api.get("/cash")
    assert any(e["id"] == STATE["draw_today"] for e in ours["data"]["entries"])


def test_cash_routes_require_login(anon: Api) -> None:
    assert anon.get("/cash")[0] == 401
    assert anon.post("/cash", {"type": "DRAW", "amount": 1})[0] == 401
    assert anon.get("/cash/summary")[0] == 401
