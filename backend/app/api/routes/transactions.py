"""Whole-business transaction feed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"], responses=ERROR_RESPONSES)


@router.get("")
def list_transactions(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    type: str = Query(""),
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    limit: str = Query(""),
) -> dict:
    transactions = transaction_service.list_for_user(
        db,
        user_id,
        type_=type or "",
        date_from=v.require_date(date_from, "From date") if date_from else "",
        date_to=v.require_date(date_to, "To date") if date_to else "",
        limit=limit or 200,
    )
    return ok(transactions)


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    tid = v.require_id(transaction_id, "Transaction ID")
    transaction = transaction_service.find_by_id(db, user_id, tid)
    if transaction is None:
        raise ApiError.not_found("Transaction not found.")
    return ok(transaction)


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    tid = v.require_id(transaction_id, "Transaction ID")
    transaction_service.remove(db, user_id, tid)
    return ok({"message": "Transaction deleted."})
