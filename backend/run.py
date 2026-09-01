"""Entry point: check the database is reachable, then start serving.

    python run.py                 (or: uvicorn app.main:app --reload)
"""

from __future__ import annotations

import sys

import uvicorn
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


def main() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — the message is the whole point
        print(f"Could not connect to PostgreSQL: {exc}", file=sys.stderr)
        print(
            "Check DATABASE_URL in backend/.env and that PostgreSQL is running.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    print(f"Credit Book running at http://localhost:{settings.port}")
    print(f"API           http://localhost:{settings.port}/api")
    print(f"Docs          http://localhost:{settings.port}/api/docs")
    print(f"Environment   {settings.node_env}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_production,
        log_level="info",
    )


if __name__ == "__main__":
    main()
