"""Customer routes, plus the customer's own ledger.

Port of src/controllers/customer.controller.js and the two customer-scoped
handlers in src/controllers/transaction.controller.js. A customer's ledger
lives under the customer, exactly as before.
"""

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
from app.schemas.customer import CustomerWriteRequest
from app.schemas.transaction import TransactionCreateRequest
from app.services import customer_service, transaction_service

router = APIRouter(prefix="/customers", tags=["customers"], responses=ERROR_RESPONSES)

MAX_ITEMS = 50
MAX_QUANTITY = 100000


@router.get("")
def list_customers(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    search: str = Query(""),
    q: str = Query(""),
    customer_status: str = Query("", alias="status"),
) -> dict:
    return ok(
        customer_service.list_customers(
            db, user_id, search=search or q, status=customer_status
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerWriteRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    customer = customer_service.create(
        db,
        user_id,
        {
            "fullName": v.require_string(
                payload.fullName or payload.name, "Full name", max_length=120
            ),
            "phone": v.require_phone(payload.phone),
            "email": v.optional_email(payload.email),
            "address": v.optional_string(
                payload.address or payload.area, "Address", max_length=200
            ),
            "gender": v.optional_gender(payload.gender),
            "notes": v.optional_string(payload.notes, "Notes", max_length=1000),
        },
    )
    return ok(customer)


@router.get("/{customer_id}")
def get_customer(
    customer_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    cid = v.require_id(customer_id, "Customer ID")
    return ok(customer_service.find_by_id_or_fail(db, user_id, cid))


@router.api_route("/{customer_id}", methods=["PUT", "PATCH"])
def update_customer(
    customer_id: str,
    payload: CustomerWriteRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    """PUT and PATCH share this: only the keys actually sent are updated."""
    cid = v.require_id(customer_id, "Customer ID")
    body = payload.model_dump(exclude_unset=True)
    patch: dict[str, Any] = {}

    name = body["fullName"] if "fullName" in body else body.get("name")
    if "fullName" in body or "name" in body:
        patch["fullName"] = v.require_string(name, "Full name", max_length=120)
    if "phone" in body:
        patch["phone"] = v.require_phone(body["phone"])
    if "email" in body:
        patch["email"] = v.optional_email(body["email"])

    address = body["address"] if "address" in body else body.get("area")
    if "address" in body or "area" in body:
        patch["address"] = v.optional_string(address, "Address", max_length=200)
    if "gender" in body:
        patch["gender"] = v.optional_gender(body["gender"])
    if "notes" in body:
        patch["notes"] = v.optional_string(body["notes"], "Notes", max_length=1000)

    return ok(customer_service.update(db, user_id, cid, patch))


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    cid = v.require_id(customer_id, "Customer ID")
    customer_service.remove(db, user_id, cid)
    return ok({"message": "Customer deleted."})


# ----------------------------------------------------- the customer's ledger --
@router.get("/{customer_id}/transactions")
def list_customer_transactions(
    customer_id: str,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    cid = v.require_id(customer_id, "Customer ID")
    customer = customer_service.find_by_id_or_fail(db, user_id, cid)
    transactions = transaction_service.list_for_customer(db, user_id, cid)
    return ok({"customer": customer, "transactions": transactions})


def parse_items(raw_items: Any) -> list[dict[str, Any]]:
    """Validates the line items of a multi-item credit.

    Errors name the offending row ("Item 2: …") because a form with six rows is
    unusable if the message only says something is wrong somewhere.
    """
    if not isinstance(raw_items, list):
        raise ApiError.bad_request("Items must be a list.")
    if len(raw_items) == 0:
        raise ApiError.bad_request("Add at least one item.")
    if len(raw_items) > MAX_ITEMS:
        raise ApiError.bad_request(f"A transaction cannot have more than {MAX_ITEMS} items.")

    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        label = f"Item {index + 1}"

        if not isinstance(raw, dict):
            raise ApiError.bad_request(f"{label} is not valid.")

        name = v.require_string(raw.get("name"), f"{label} name", max_length=120)

        quantity = raw.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
            raise ApiError.bad_request(f"{label} ({name}): quantity must be a whole number.")
        if isinstance(quantity, float) and not quantity.is_integer():
            raise ApiError.bad_request(f"{label} ({name}): quantity must be a whole number.")
        quantity = int(quantity)
        if quantity < 1:
            raise ApiError.bad_request(f"{label} ({name}): quantity must be at least 1.")
        if quantity > MAX_QUANTITY:
            raise ApiError.bad_request(f"{label} ({name}): quantity is too large.")

        price = parse_amount(raw.get("unitPrice"), field=f"{label} ({name}) unit price")
        if not price.ok:
            raise ApiError.bad_request(price.message)

        parsed.append({"name": name, "quantity": quantity, "unitPrice": price.value})

    return parsed


@router.post("/{customer_id}/transactions", status_code=status.HTTP_201_CREATED)
def create_customer_transaction(
    customer_id: str,
    payload: TransactionCreateRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    cid = v.require_id(customer_id, "Customer ID")
    type_ = v.require_enum(payload.type, ["CREDIT", "PAYMENT"], "Transaction type")

    has_items = payload.items is not None

    if has_items and type_ == "PAYMENT":
        raise ApiError.bad_request("A payment cannot have item lines.")

    data: dict[str, Any] = {"type": type_}

    if has_items:
        data["items"] = parse_items(payload.items)
        # Optional override; otherwise the service summarises the items.
        if str(payload.description or "").strip():
            data["description"] = v.require_string(
                payload.description, "Description", max_length=200
            )
    else:
        amount = parse_amount(payload.amount)
        if not amount.ok:
            raise ApiError.bad_request(amount.message)
        data["amount"] = amount.value

        # Credit must say what was bought. A payment defaults to "Payment
        # received" rather than blocking the owner over a field they'd have
        # typed anyway.
        has_description = str(payload.description or "").strip() != ""
        data["description"] = (
            "Payment received"
            if not has_description and type_ == "PAYMENT"
            else v.require_string(payload.description, "Description", max_length=200)
        )

    due_date = v.optional_date(payload.dueDate, "Due date")
    if type_ == "PAYMENT" and due_date:
        raise ApiError.bad_request("A payment cannot have a due date.")
    data["dueDate"] = due_date
    data["notes"] = v.optional_string(payload.notes, "Notes", max_length=1000)
    data["signature"] = v.optional_image(payload.signature, "Signature")
    data["productPhoto"] = v.optional_image(payload.productPhoto, "Product photo")

    transaction = transaction_service.create(db, user_id, cid, data)

    # Return the customer too — every caller immediately needs the new balance.
    customer = customer_service.find_by_id(db, user_id, cid)

    return ok({"transaction": transaction, "customer": customer})
