"""Quick-entry item routes. Port of src/controllers/item.controller.js."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.core.money import parse_amount
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.schemas.item import ItemCreateRequest
from app.services import item_service

router = APIRouter(prefix="/items", tags=["items"], responses=ERROR_RESPONSES)


@router.get("")
def list_items(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    return ok(item_service.list_items(db, user_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    price = parse_amount(payload.price, field="Price")
    if not price.ok:
        raise ApiError.bad_request(price.message)

    name = v.require_string(payload.name, "Item name", max_length=80)
    return ok(item_service.create(db, user_id, name, price.value))


@router.delete("/{item_id}")
def delete_item(
    item_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    iid = v.require_id(item_id, "Item ID")
    item_service.remove(db, user_id, iid)
    return ok({"message": "Item deleted."})
