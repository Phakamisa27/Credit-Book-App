"""Product / stock routes.

GET, POST and DELETE are the Credit Book's quick-item endpoints, extended with
stock fields. PATCH is new for ThathaCash: updating a stock count.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.core.money import parse_amount
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.common import ERROR_RESPONSES, ok
from app.schemas.item import ItemCreateRequest, ItemUpdateRequest
from app.services import item_service

router = APIRouter(prefix="/items", tags=["items"], responses=ERROR_RESPONSES)


def parse_price(value: Any) -> Any:
    price = parse_amount(value, field="Price")
    if not price.ok:
        raise ApiError.bad_request(price.message)
    return price.value


def parse_stock_fields(body: dict[str, Any]) -> dict[str, int]:
    """Validates whichever stock fields were sent; ignores the rest."""
    fields: dict[str, int] = {}
    if body.get("quantity") is not None:
        fields["quantity"] = v.require_whole_number(body["quantity"], "Quantity")
    if body.get("lowStockLevel") is not None:
        fields["lowStockLevel"] = v.require_whole_number(
            body["lowStockLevel"], "Running low level"
        )
    if body.get("reorderQuantity") is not None:
        fields["reorderQuantity"] = v.require_whole_number(
            body["reorderQuantity"], "Order quantity", minimum=1
        )
    return fields


@router.get("")
def list_items(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    return ok(item_service.list_items(db, user_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    price = parse_price(payload.price)
    name = v.require_string(payload.name, "Item name", max_length=80)
    stock = parse_stock_fields(payload.model_dump())
    return ok(item_service.create(db, user_id, {"name": name, "price": price, **stock}))


@router.patch("/{item_id}")
def update_item(
    item_id: str,
    payload: ItemUpdateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    """e.g. {"quantity": 12} after counting the shelf."""
    iid = v.require_id(item_id, "Item ID")
    body = payload.model_dump(exclude_unset=True)

    patch: dict[str, Any] = parse_stock_fields(body)
    if "name" in body:
        patch["name"] = v.require_string(body["name"], "Item name", max_length=80)
    if "price" in body:
        patch["price"] = parse_price(body["price"])

    return ok(item_service.update(db, user_id, iid, patch))


@router.delete("/{item_id}")
def delete_item(
    item_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    iid = v.require_id(item_id, "Item ID")
    item_service.remove(db, user_id, iid)
    return ok({"message": "Item deleted."})
