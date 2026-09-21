"""ThathaCash Home screen and suggested order."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.services import cash_service, home_service, item_service

router = APIRouter(tags=["home"], responses=ERROR_RESPONSES)


@router.get("/home")
def home(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    """Everything the Home screen renders, in one request."""
    return ok(home_service.home(db, user_id))


@router.get("/order")
def suggested_order(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    """What to buy next, and whether it fits the stock budget."""
    budget = cash_service.available_for_stock(db, user_id)
    return ok(item_service.suggested_order(db, user_id, budget))
