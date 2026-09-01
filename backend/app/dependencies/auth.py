"""JWT authentication dependency.

The token carries the user id. Every protected route depends on
`get_current_user_id`, and every query then filters by it — so a row can only
ever be read or written by the account that owns it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.errors import ApiError
from app.core.security import TokenExpired, TokenInvalid, read_token


def get_current_user_id(request: Request) -> int:
    header = request.headers.get("authorization") or ""
    scheme, _, token = header.partition(" ")

    if scheme != "Bearer" or not token:
        raise ApiError.unauthorized()

    try:
        return read_token(token)
    except TokenExpired:
        raise ApiError.unauthorized("Your session has expired. Please log in again.") from None
    except TokenInvalid:
        raise ApiError.unauthorized() from None


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
