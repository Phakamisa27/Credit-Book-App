"""PostgreSQL engine and session factory.

Every query in this app goes through a Session and is parameterised. No SQL
string is ever built from user input — the raw `text()` statements used for the
aggregate reports all take bound parameters.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _normalise(url: str) -> str:
    # SQLAlchemy wants an explicit driver; the .env keeps the libpq form that
    # node-postgres and psql both understand.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


engine = create_engine(
    _normalise(settings.database_url),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
