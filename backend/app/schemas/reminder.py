from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class ReminderWriteRequest(RequestModel):
    customerId: Any = None
    amount: Any = None
    dueDate: Any = None
    status: Any = None
    notes: Any = None
