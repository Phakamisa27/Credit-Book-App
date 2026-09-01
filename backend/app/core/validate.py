"""Small hand-rolled validators.

Port of src/utils/validate.js. Pydantic describes the request shapes; these
functions produce the messages. That split is deliberate: the 400-level text is
copy the shop owner reads ("must be a valid South African number, e.g.
074 099 8882"), not a developer-facing schema dump, and the frontend renders
`message` verbatim.
"""

from __future__ import annotations

import re
from datetime import date

from app.core.errors import ApiError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IMAGE_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif);base64,[A-Za-z0-9+/=]+$")
_NON_DIGITS = re.compile(r"\D")


def require_string(value: object, field: str, *, min_length: int = 1, max_length: int = 200) -> str:
    if not isinstance(value, str):
        raise ApiError.bad_request(f"{field} is required.")
    trimmed = value.strip()
    if len(trimmed) < min_length:
        raise ApiError.bad_request(f"{field} is required.")
    if len(trimmed) > max_length:
        raise ApiError.bad_request(f"{field} must be {max_length} characters or fewer.")
    return trimmed


def optional_string(value: object, field: str, *, max_length: int = 500) -> str | None:
    """Returns None for empty input rather than raising — for optional fields."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError.bad_request(f"{field} must be text.")
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > max_length:
        raise ApiError.bad_request(f"{field} must be {max_length} characters or fewer.")
    return trimmed


def require_phone(value: object, field: str = "Phone number") -> str:
    """South African numbers: 10 digits starting with 0, or the same in +27 form.

    Stored exactly as the owner typed it, but the digits have to make sense.
    """
    raw = require_string(value, field, max_length=20)
    digits = _NON_DIGITS.sub("", raw)

    if len(digits) == 10 and digits.startswith("0"):
        return raw
    if len(digits) == 11 and digits.startswith("27"):
        return raw

    raise ApiError.bad_request(
        f"{field} must be a valid South African number, e.g. 074 099 8882."
    )


def require_email(value: object, field: str = "Email") -> str:
    raw = require_string(value, field, max_length=254).lower()
    # Deliberately loose: one @, something either side, a dot in the domain.
    if not _EMAIL_RE.match(raw):
        raise ApiError.bad_request(f"{field} must be a valid email address.")
    return raw


def optional_email(value: object, field: str = "Email") -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return require_email(value, field)


def require_date(value: object, field: str = "Date") -> str:
    """Accepts YYYY-MM-DD only, and checks the date really exists (rejects 2026-02-30)."""
    raw = require_string(value, field, max_length=10)
    if not _DATE_RE.match(raw):
        raise ApiError.bad_request(f"{field} must be in YYYY-MM-DD format.")
    year, month, day = (int(part) for part in raw.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        raise ApiError.bad_request(f"{field} is not a real date.") from None
    return raw


def optional_date(value: object, field: str = "Date") -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return require_date(value, field)


def require_enum(value: object, allowed: list[str], field: str) -> str:
    raw = value.strip().upper() if isinstance(value, str) else ""
    if raw not in allowed:
        raise ApiError.bad_request(f"{field} must be one of: {', '.join(allowed)}.")
    return raw


def optional_gender(value: object) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip().lower()
    if raw not in ("male", "female"):
        raise ApiError.bad_request("Gender must be male or female.")
    return raw


def require_id(value: object, field: str = "ID") -> int:
    """Route params are always strings; ids must be positive integers."""
    if isinstance(value, bool):
        raise ApiError.bad_request(f"{field} is not valid.")
    try:
        if isinstance(value, str):
            if not re.fullmatch(r"[+-]?\d+", value.strip()):
                raise ValueError(value)
            number = int(value.strip())
        elif isinstance(value, int):
            number = value
        elif isinstance(value, float):
            if not float(value).is_integer():
                raise ValueError(value)
            number = int(value)
        else:
            raise ValueError(value)
    except (TypeError, ValueError):
        raise ApiError.bad_request(f"{field} is not valid.") from None

    if number < 1:
        raise ApiError.bad_request(f"{field} is not valid.")
    return number


def optional_image(value: object, field: str = "Image") -> str | None:
    """Signatures and product photos arrive as data: URIs from the canvas / file
    input. Anything else is rejected so the column cannot become a link to a
    remote resource.
    """
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    if not _IMAGE_RE.match(raw):
        raise ApiError.bad_request(f"{field} must be an uploaded image.")
    if len(raw) > 4_000_000:
        raise ApiError.bad_request(f"{field} is too large. Please use a smaller photo.")
    return raw
