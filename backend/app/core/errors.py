"""Centralised error handling.

The rule, unchanged from the Express backend: technical detail is logged on the
server, never sent to the browser. The owner sees a sentence they can act on.

Anything raised that is NOT an ApiError is treated as a bug or an
infrastructure failure: logged in full, and the client only ever sees
"Something went wrong. Please try again."
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("creditbook")

GENERIC_MESSAGE = "Something went wrong. Please try again."

# Postgres error codes we can turn into a helpful message.
PG_MESSAGES: dict[str, str] = {
    "23505": "That record already exists.",  # unique_violation
    "23503": "That record is linked to something else and cannot be used.",  # foreign_key_violation
    "23514": "Some of the details you entered are not valid.",  # check_violation
    "22003": "That amount is too large.",  # numeric_value_out_of_range
}

# Unique constraints, named so the message can be specific.
CONSTRAINT_MESSAGES: dict[str, str] = {
    "users_email_key": "An account with that email already exists.",
    "customers_owner_phone_unique": "You already have a customer with that phone number.",
    "items_owner_name_unique": "You already have a quick item with that name.",
}


class ApiError(Exception):
    """An error that is safe to show the user."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message

    @staticmethod
    def bad_request(message: str) -> "ApiError":
        return ApiError(400, message)

    @staticmethod
    def unauthorized(message: str = "Please log in to continue.") -> "ApiError":
        return ApiError(401, message)

    @staticmethod
    def forbidden(message: str = "You do not have access to that.") -> "ApiError":
        return ApiError(403, message)

    @staticmethod
    def not_found(message: str = "Not found.") -> "ApiError":
        return ApiError(404, message)

    @staticmethod
    def conflict(message: str) -> "ApiError":
        return ApiError(409, message)


def fail(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": False, "message": message})


def _db_error_response(exc: DBAPIError, request: Request) -> JSONResponse | None:
    """Maps a Postgres error onto the same 409 the Express backend returned."""
    orig: Any = getattr(exc, "orig", None)
    code = getattr(orig, "pgcode", None)
    constraint = None
    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint = getattr(diag, "constraint_name", None)

    message = CONSTRAINT_MESSAGES.get(constraint or "") or PG_MESSAGES.get(code or "")
    if not message:
        return None

    logger.error("[db %s] %s %s: %s", code, request.method, request.url.path, orig)
    return fail(409, message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return fail(exc.status, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # A body that is not valid JSON at all — express.json() answered this
        # with the same message and status.
        for error in exc.errors():
            if error.get("type") in {"json_invalid", "value_error.jsondecode"}:
                return fail(400, "Invalid request format.")
        return fail(400, "Invalid request format.")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else GENERIC_MESSAGE
        if exc.status_code == 404:
            detail = "That endpoint does not exist."
        elif exc.status_code == 405:
            detail = "That endpoint does not exist."
        elif exc.status_code == 413:
            detail = "That upload is too large. Please use a smaller photo."
        return fail(exc.status_code, detail)

    @app.exception_handler(IntegrityError)
    async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        response = _db_error_response(exc, request)
        if response is not None:
            return response
        logger.exception("[error] %s %s", request.method, request.url.path)
        return fail(500, GENERIC_MESSAGE)

    @app.exception_handler(DBAPIError)
    async def _dbapi_error(request: Request, exc: DBAPIError) -> JSONResponse:
        response = _db_error_response(exc, request)
        if response is not None:
            return response
        logger.exception("[error] %s %s", request.method, request.url.path)
        return fail(500, GENERIC_MESSAGE)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Anything else is a bug or an outage. Log everything, expose nothing.
        logger.exception("[error] %s %s", request.method, request.url.path)
        return fail(500, GENERIC_MESSAGE)
