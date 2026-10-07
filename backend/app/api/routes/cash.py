"""Cash entry routes (ThathaCash): log money in, expenses, stock purchases and
draws, list them for a period, and record a till recount."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.core.money import parse_amount
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.models.cash_entry import ALL_CASH_TYPES, CASH_TYPES
from app.schemas.cash import CashCountRequest, CashEntryCreateRequest
from app.schemas.common import ERROR_RESPONSES, ok
from app.services import cash_service

router = APIRouter(prefix="/cash", tags=["cash"], responses=ERROR_RESPONSES)


@router.get("")
def list_entries(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    type: str = Query(""),
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
) -> dict:
    """GET /api/cash?type=DRAW&from=2026-09-01&to=2026-09-30"""
    type_ = v.require_enum(type, ALL_CASH_TYPES, "Type") if type else ""
    return ok(
        cash_service.list_entries(
            db,
            user_id,
            type_=type_,
            date_from=v.require_date(date_from, "From date") if date_from else "",
            date_to=v.require_date(date_to, "To date") if date_to else "",
        )
    )


@router.get("/summary")
def summary(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    """Cash available, the stock budget and draws this month."""
    return ok(cash_service.cash_summary(db, user_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: CashEntryCreateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    type_ = v.require_enum(payload.type, CASH_TYPES, "Type")

    amount = parse_amount(payload.amount)
    if not amount.ok:
        raise ApiError.bad_request(amount.message)

    return ok(
        cash_service.create(
            db,
            user_id,
            {
                "type": type_,
                "amount": amount.value,
                "note": v.optional_string(payload.note, "Note", max_length=200),
                "date": v.optional_date(payload.date, "Date"),
            },
        )
    )


@router.post("/count")
def count_cash(
    payload: CashCountRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/cash/count {"amount": 1840} — the cash the owner just counted.

    R0 is allowed: an empty till is a real count.
    """
    counted = v.require_rands_or_zero(payload.amount, "Cash counted")
    return ok(cash_service.record_count(db, user_id, counted))


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    """For mistakes. Cash available recalculates because it is never stored."""
    eid = v.require_id(entry_id, "Entry ID")
    cash_service.remove(db, user_id, eid)
    return ok({"message": "Entry deleted."})
