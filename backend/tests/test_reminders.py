"""Payment reminders."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import Api

STATE: dict[str, int] = {}


@pytest.fixture(scope="module")
def reminder_customer(new_customer) -> int:
    return new_customer("Reminder Test")


def test_rejects_a_reminder_for_a_customer_that_does_not_exist(api: Api) -> None:
    status, _ = api.post(
        "/reminders", {"customerId": 99999999, "amount": 100, "dueDate": "2030-01-01"}
    )
    assert status == 404


def test_rejects_a_reminder_with_no_due_date(api: Api, reminder_customer: int) -> None:
    status, body = api.post("/reminders", {"customerId": reminder_customer, "amount": 100})
    assert status == 400
    assert "Due date" in body["message"]


def test_creates_a_reminder(api: Api, reminder_customer: int) -> None:
    status, body = api.post(
        "/reminders",
        {
            "customerId": reminder_customer,
            "amount": 350,
            "dueDate": "2030-01-01",
            "notes": "Follow up",
        },
    )
    assert status == 201
    assert body["data"]["amount"] == 350
    assert body["data"]["status"] == "PENDING"
    assert body["data"]["customerName"] == "Reminder Test"
    assert body["data"]["urgency"] == "UPCOMING"
    STATE["reminder_id"] = body["data"]["id"]


def test_marks_a_past_due_reminder_as_overdue(api: Api, reminder_customer: int) -> None:
    past = (date.today() - timedelta(days=3)).isoformat()
    _, body = api.post(
        "/reminders", {"customerId": reminder_customer, "amount": 100, "dueDate": past}
    )
    assert body["data"]["urgency"] == "OVERDUE"


def test_marks_a_reminder_due_today(api: Api, reminder_customer: int) -> None:
    _, body = api.post(
        "/reminders",
        {"customerId": reminder_customer, "amount": 100, "dueDate": date.today().isoformat()},
    )
    assert body["data"]["urgency"] == "DUE_TODAY"


def test_reads_one_reminder_by_id(api: Api) -> None:
    status, body = api.get(f"/reminders/{STATE['reminder_id']}")
    assert status == 200
    assert body["data"]["amount"] == 350


def test_updates_a_reminder_status(api: Api) -> None:
    status, body = api.patch(f"/reminders/{STATE['reminder_id']}", {"status": "SENT"})
    assert status == 200
    assert body["data"]["status"] == "SENT"


def test_rejects_an_unknown_status(api: Api) -> None:
    status, _ = api.patch(f"/reminders/{STATE['reminder_id']}", {"status": "MAYBE"})
    assert status == 400


def test_filters_by_customer(api: Api, reminder_customer: int) -> None:
    _, body = api.get(f"/reminders?customerId={reminder_customer}")
    assert body["data"]
    assert all(r["customerId"] == reminder_customer for r in body["data"])


def test_filters_to_open_reminders_only(api: Api) -> None:
    api.patch(f"/reminders/{STATE['reminder_id']}", {"status": "DONE"})
    _, body = api.get("/reminders?status=OPEN")
    assert not any(r["id"] == STATE["reminder_id"] for r in body["data"])


def test_a_closed_reminder_reports_closed_urgency(api: Api) -> None:
    _, body = api.get(f"/reminders/{STATE['reminder_id']}")
    assert body["data"]["status"] == "DONE"
    assert body["data"]["urgency"] == "CLOSED"


def test_deletes_a_reminder(api: Api) -> None:
    status, _ = api.delete(f"/reminders/{STATE['reminder_id']}")
    assert status == 200
    assert api.get(f"/reminders/{STATE['reminder_id']}")[0] == 404


def test_deleting_a_customer_takes_their_reminders_with_them(api: Api, new_customer) -> None:
    customer_id = new_customer("Reminder Cascade")
    _, created = api.post(
        "/reminders", {"customerId": customer_id, "amount": 75, "dueDate": "2030-06-01"}
    )
    reminder_id = created["data"]["id"]

    assert api.delete(f"/customers/{customer_id}")[0] == 200
    assert api.get(f"/reminders/{reminder_id}")[0] == 404
