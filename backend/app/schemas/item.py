from __future__ import annotations

from typing import Any

from app.schemas.common import RequestModel


class ItemCreateRequest(RequestModel):
    name: Any = None
    price: Any = None
