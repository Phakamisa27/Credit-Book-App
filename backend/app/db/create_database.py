"""Creates the database named in DATABASE_URL, if it does not already exist.

Connects to the server's default "postgres" database to do it, because you
cannot create a database from inside the one you are creating.

    python -m app.db.create_database
"""

from __future__ import annotations

import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.engine import make_url

from app.core.config import settings


def create_database() -> None:
    url = make_url(settings.database_url)
    db_name = url.database

    if not db_name:
        raise SystemExit("DATABASE_URL has no database name.")

    # Same credentials and host, but pointed at the default database.
    admin_url = url.set(database="postgres", drivername="postgresql")

    connection = psycopg2.connect(admin_url.render_as_string(hide_password=False))
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cursor.fetchone():
                print(f'Database "{db_name}" already exists.')
                return

            # CREATE DATABASE cannot take a parameter, so quote the identifier
            # instead. The name comes from our own .env, not from user input.
            escaped = db_name.replace('"', '""')
            cursor.execute(f'CREATE DATABASE "{escaped}"')
            print(f'Database "{db_name}" created.')
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        create_database()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — the message is the whole point
        print(f"Could not create the database: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
