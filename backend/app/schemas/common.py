"""The response envelope, unchanged from the Express backend.

    success  {"success": true,  "data": …}
    failure  {"success": false, "message": "…"}

frontend/js/api.js unwraps `payload.data` on success and reads `payload.message`
on failure, so both shapes are part of the contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RequestModel(BaseModel):
    """Base for request bodies.

    Fields are deliberately untyped (`Any`): the user-facing 400 messages come
    from app/core/validate.py, which produces sentences the shop owner can act
    on, rather than a schema dump. Unknown keys are ignored, exactly as
    `req.body.whatever` was.
    """

    model_config = ConfigDict(extra="ignore")


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str


def ok(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Validation failed"},
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflicts with an existing record"},
    500: {"model": ErrorResponse, "description": "Unexpected server error"},
}
