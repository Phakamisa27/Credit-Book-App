"""Accounts and the business profile.

One owner uses this app, so there is no role system, no invitations and no
password-reset email flow. What there is: a properly hashed password and a
token that scopes every query to the account that made it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.money import to_amount
from app.core.security import dummy_verify, hash_password, verify_password
from app.core.serialize import iso_utc
from app.repositories import user_repo


def to_api(row: Any) -> dict[str, Any] | None:
    """Never return password_hash. Every read of a user goes through this."""
    if row is None:
        return None
    return {
        "id": row["id"],
        "fullName": row["full_name"],
        "email": row["email"],
        "businessName": row["business_name"] or "",
        "businessPhone": row["business_phone"] or "",
        "profileImage": row["profile_image"] or "",
        # Safe to draw settings. restockReserve stays null until the owner
        # sets it, so Home can ask them to.
        "restockReserve": (
            None if row["restock_reserve"] is None else to_amount(row["restock_reserve"])
        ),
        "bufferPercent": to_amount(row["buffer_percent"]),
        "cashCountedAt": iso_utc(row["cash_counted_at"]),
        "createdAt": iso_utc(row["created_at"]),
        "updatedAt": iso_utc(row["updated_at"]),
    }


def register(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    if user_repo.exists_with_email(db, data["email"]):
        raise ApiError.conflict("An account with that email already exists.")

    row = user_repo.insert(
        db,
        {
            "full_name": data["fullName"],
            "email": data["email"],
            "password_hash": hash_password(data["password"]),
            "business_name": data.get("businessName"),
            "business_phone": data.get("businessPhone"),
        },
    )
    return to_api(row)


def login(db: Session, email: str, password: str) -> dict[str, Any]:
    row = user_repo.find_by_email(db, email)

    # Same message whether the email is unknown or the password is wrong — do
    # not confirm which emails have accounts. The dummy compare keeps the
    # response time similar either way.
    if row is None:
        dummy_verify(password)
        raise ApiError.unauthorized("Incorrect email or password.")

    if not verify_password(password, row["password_hash"]):
        raise ApiError.unauthorized("Incorrect email or password.")

    return to_api(row)


def find_by_id(db: Session, user_id: int) -> dict[str, Any] | None:
    return to_api(user_repo.find_by_id(db, user_id))


def update_profile(db: Session, user_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    row = user_repo.update_columns(db, user_id, patch)
    if row is None:
        raise ApiError.not_found("Account not found.")
    return to_api(row)


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> None:
    current_hash = user_repo.password_hash_for(db, user_id)
    if current_hash is None:
        raise ApiError.not_found("Account not found.")

    if not verify_password(current_password, current_hash):
        raise ApiError.bad_request("Your current password is incorrect.")

    user_repo.set_password_hash(db, user_id, hash_password(new_password))


def account_exists(db: Session) -> bool:
    """True once any account exists. The login page uses this to decide whether
    to show "Register" — a single-owner app should not invite strangers to sign
    up once the owner has their account."""
    return user_repo.any_account_exists(db)
