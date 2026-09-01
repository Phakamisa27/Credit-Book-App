from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.serialize import iso_utc
from app.schemas.common import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return ok({"status": "ok", "time": iso_utc(datetime.now(tz=timezone.utc))})
