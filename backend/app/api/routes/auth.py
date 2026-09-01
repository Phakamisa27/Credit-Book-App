"""Authentication routes.

/auth/status, /auth/register, /auth/login and /auth/logout are public; the rest
require a token. Port of src/controllers/auth.controller.js.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import validate as v
from app.core.errors import ApiError
from app.core.security import sign_token
from app.db.session import get_db
from app.dependencies.auth import CurrentUserId
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, UpdateMeRequest
from app.schemas.common import ERROR_RESPONSES, ok
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)

MIN_PASSWORD = 8


def require_password(value: Any, field: str = "Password") -> str:
    if not isinstance(value, str) or len(value) < MIN_PASSWORD:
        raise ApiError.bad_request(f"{field} must be at least {MIN_PASSWORD} characters.")
    if len(value) > 200:
        raise ApiError.bad_request(f"{field} is too long.")
    return value


# ------------------------------------------------------------------ public ---
@router.get("/status")
def account_status(db: Session = Depends(get_db)) -> dict:
    """Lets the login page hide registration once the owner has an account."""
    return ok({"accountExists": auth_service.account_exists(db)})


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    body = payload.model_dump(exclude_unset=True)

    full_name = v.require_string(payload.fullName, "Full name", max_length=120)
    email = v.require_email(payload.email)
    password = require_password(payload.password)
    business_name = v.optional_string(payload.businessName, "Business name", max_length=120)
    business_phone = (
        v.require_phone(payload.businessPhone, "Business phone") if payload.businessPhone else None
    )

    if "confirmPassword" in body and body["confirmPassword"] != password:
        raise ApiError.bad_request("Passwords do not match.")

    user = auth_service.register(
        db,
        {
            "fullName": full_name,
            "email": email,
            "password": password,
            "businessName": business_name,
            "businessPhone": business_phone,
        },
    )

    return ok({"user": user, "token": sign_token(user["id"])})


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    email = v.require_email(payload.email)
    password = v.require_string(payload.password, "Password", max_length=200)

    user = auth_service.login(db, email, password)
    return ok({"user": user, "token": sign_token(user["id"])})


@router.post("/logout")
def logout() -> dict:
    """Tokens are stateless, so "logging out" is the client discarding its
    token. The endpoint exists so the frontend has one obvious thing to call."""
    return ok({"message": "Logged out."})


# --------------------------------------------------------------- protected ---
@router.get("/me")
def me(user_id: CurrentUserId, db: Session = Depends(get_db)) -> dict:
    user = auth_service.find_by_id(db, user_id)
    if user is None:
        raise ApiError.unauthorized()
    return ok(user)


@router.api_route("/me", methods=["PATCH", "PUT"])
def update_me(
    payload: UpdateMeRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    body = payload.model_dump(exclude_unset=True)
    patch: dict[str, Any] = {}

    if "fullName" in body:
        patch["fullName"] = v.require_string(body["fullName"], "Full name", max_length=120)
    if "businessName" in body:
        patch["businessName"] = v.optional_string(
            body["businessName"], "Business name", max_length=120
        )
    if "businessPhone" in body:
        patch["businessPhone"] = (
            v.require_phone(body["businessPhone"], "Business phone")
            if body["businessPhone"]
            else None
        )
    if "profileImage" in body:
        patch["profileImage"] = v.optional_image(body["profileImage"], "Profile photo")

    return ok(auth_service.update_profile(db, user_id, patch))


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
) -> dict:
    body = payload.model_dump(exclude_unset=True)

    current_password = v.require_string(payload.currentPassword, "Current password", max_length=200)
    new_password = require_password(payload.newPassword, "New password")

    if "confirmPassword" in body and body["confirmPassword"] != new_password:
        raise ApiError.bad_request("New passwords do not match.")

    auth_service.change_password(db, user_id, current_password, new_password)
    return ok({"message": "Password updated."})
