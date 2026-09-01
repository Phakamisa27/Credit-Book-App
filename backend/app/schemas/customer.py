from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class CustomerWriteRequest(RequestModel):
    """Create and update share this shape.

    `name`/`area` are accepted as aliases for `fullName`/`address` because the
    older frontend forms posted those keys; both spellings are still honoured.
    """

    fullName: Any = None
    name: Any = None
    phone: Any = None
    email: Any = None
    address: Any = None
    area: Any = None
    gender: Any = None
    notes: Any = None
