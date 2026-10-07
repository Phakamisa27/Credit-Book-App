from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class CashEntryCreateRequest(RequestModel):
    """{"type": "DRAW", "amount": 200, "note": "Personal", "date": "2026-09-17"}

    `note` and `date` are optional; `date` defaults to today.
    """

    type: Any = None
    amount: Any = None
    note: Any = None
    date: Any = None


class CashCountRequest(RequestModel):
    """{"amount": 1840} — the cash the owner counted in the till just now."""

    amount: Any = None
