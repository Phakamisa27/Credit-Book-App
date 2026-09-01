"""The declarative base every model inherits from.

Kept free of model imports so there is no import cycle: whoever needs the full
metadata (Alembic, the test bootstrap) imports `app.models` as well, which
registers all six tables on `Base.metadata`.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
