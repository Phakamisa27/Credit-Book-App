"""Reminder routes. Port of src/controllers/reminder.controller.js."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.core.money import parse_amount
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.schemas.reminder import ReminderWriteRequest
from app.services import reminder_service

router = APIRouter(prefix="/reminders", tags=["reminders"], responses=ERROR_RESPONSES)


@router.get("")
def list_reminders(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    status_filter: str = Query("", alias="status"),
    customerId: str = Query(""),
) -> dict:
    customer_id = v.require_id(customerId, "Customer ID") if customerId else None
    return ok(
        reminder_service.list_reminders(
            db, user_id, status=status_filter, customer_id=customer_id
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderWriteRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    amount = parse_amount(payload.amount, field="Reminder amount")
    if not amount.ok:
        raise ApiError.bad_request(amount.message)

    reminder = reminder_service.create(
        db,
        user_id,
        {
            "customerId": v.require_id(payload.customerId, "Customer ID"),
            "amount": amount.value,
            "dueDate": v.require_date(payload.dueDate, "Due date"),
            "status": (
                v.require_enum(payload.status, reminder_service.STATUSES, "Status")
                if payload.status
                else "PENDING"
            ),
            "notes": v.optional_string(payload.notes, "Notes", max_length=1000),
        },
    )
    return ok(reminder)


@router.get("/{reminder_id}")
def get_reminder(
    reminder_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    rid = v.require_id(reminder_id, "Reminder ID")
    reminder = reminder_service.find_by_id(db, user_id, rid)
    if reminder is None:
        raise ApiError.not_found("Reminder not found.")
    return ok(reminder)


@router.api_route("/{reminder_id}", methods=["PUT", "PATCH"])
def update_reminder(
    reminder_id: str,
    payload: ReminderWriteRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    rid = v.require_id(reminder_id, "Reminder ID")
    body = payload.model_dump(exclude_unset=True)
    patch: dict[str, Any] = {}

    if "amount" in body:
        amount = parse_amount(body["amount"], field="Reminder amount")
        if not amount.ok:
            raise ApiError.bad_request(amount.message)
        patch["amount"] = amount.value
    if "dueDate" in body:
        patch["dueDate"] = v.require_date(body["dueDate"], "Due date")
    if "status" in body:
        patch["status"] = v.require_enum(body["status"], reminder_service.STATUSES, "Status")
    if "notes" in body:
        patch["notes"] = v.optional_string(body["notes"], "Notes", max_length=1000)

    return ok(reminder_service.update(db, user_id, rid, patch))


@router.delete("/{reminder_id}")
def delete_reminder(
    reminder_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    rid = v.require_id(reminder_id, "Reminder ID")
    reminder_service.remove(db, user_id, rid)
    return ok({"message": "Reminder deleted."})
