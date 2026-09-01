"""Report routes. Port of src/controllers/report.controller.js."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"], responses=ERROR_RESPONSES)


@router.get("")
def full_report(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    days: str = Query("30"),
) -> dict:
    """GET /api/reports?days=30 — the full reports page."""
    try:
        wanted = int(float(days))
    except (TypeError, ValueError):
        wanted = 30
    if wanted <= 0:
        wanted = 30
    wanted = min(max(wanted, 1), 365)

    return ok(report_service.report(db, user_id, wanted))


@router.get("/summary")
def summary(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    """Headline figures only."""
    return ok(report_service.totals(db, user_id))


@router.get("/dashboard")
def dashboard(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    """Everything the dashboard renders, one request."""
    return ok(report_service.dashboard(db, user_id))
