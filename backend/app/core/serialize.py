"""Date/time formatting for JSON responses.

The frontend was written against `JSON.stringify(new Date(...))`, which always
produces UTC with milliseconds and a trailing Z. `App.formatDateShort()` in
frontend/js/app.js slices the first ten characters of that string, so an offset
like "+02:00" would print the wrong day either side of midnight. These helpers
keep the wire format identical to the Express backend's.
"""

from __future__ import annotations

from datetime import date, datetime, timezone


def iso_utc(value: datetime | None) -> str | None:
    """2026-08-19T10:23:45.123Z — exactly what JSON.stringify(Date) emits."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    utc = value.astimezone(timezone.utc)
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{utc.microsecond // 1000:03d}Z"


def date_only(value: date | datetime | str | None) -> str | None:
    """A DATE column as a plain YYYY-MM-DD string, with no timezone shift."""
    if value is None:
        return None
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()
