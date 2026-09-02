"""Shared test fixtures.

The suite drives the real FastAPI app through TestClient, so routing,
validation, auth and SQL are all exercised together — the same end-to-end shape
the Node test suite had.

Every module gets its own throwaway account (a unique email per run) which is
deleted afterwards, so running these will not touch real books.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Redirect to the test database BEFORE any app module is imported.
#
# The suite registers and deletes accounts, so it must never run against the
# working book. app.core.config reads DATABASE_URL at import time, and
# pydantic-settings gives a real environment variable priority over .env — so
# setting it here, above the app imports below, is what takes effect.
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR / ".env")

_url = os.environ.get("DATABASE_URL", "")
if _url:
    _parts = urlparse(_url)
    _name = _parts.path.lstrip("/")
    if not _name.endswith("_test"):
        os.environ["DATABASE_URL"] = urlunparse(_parts._replace(path=f"/{_name}_test"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

# Belt and braces: if the redirect above ever fails to apply, stop the run
# rather than let DELETE FROM users loose on the real database.
if not settings.database_url.rstrip("/").endswith("_test"):
    raise RuntimeError(
        "Refusing to run: the test suite is not pointed at a _test database.\n"
        f"DATABASE_URL resolves to {urlparse(settings.database_url).path.lstrip('/')!r}.\n"
        "Create it with:  DATABASE_URL=<...>_test python -m app.db.create_database"
    )

TEST_PASSWORD = "TestPassword123"
TEST_EMAIL_DOMAIN = "creditbook.test"


class Api:
    """Small request wrapper: every call returns (status, body)."""

    def __init__(self, client: TestClient, token: str | None = None) -> None:
        self.client = client
        self.token = token

    def request(
        self,
        path: str,
        method: str = "GET",
        body: Any = None,
        auth: bool = True,
        content: str | None = None,
    ) -> tuple[int, Any]:
        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        kwargs: dict[str, Any] = {"headers": headers}
        if content is not None:
            kwargs["content"] = content
        elif body is not None:
            kwargs["json"] = body

        response = self.client.request(method, f"/api{path}", **kwargs)
        try:
            payload = response.json() if response.content else None
        except ValueError:
            payload = None
        return response.status_code, payload

    def get(self, path: str, **kw: Any) -> tuple[int, Any]:
        return self.request(path, "GET", **kw)

    def post(self, path: str, body: Any = None, **kw: Any) -> tuple[int, Any]:
        return self.request(path, "POST", body, **kw)

    def patch(self, path: str, body: Any = None, **kw: Any) -> tuple[int, Any]:
        return self.request(path, "PATCH", body, **kw)

    def put(self, path: str, body: Any = None, **kw: Any) -> tuple[int, Any]:
        return self.request(path, "PUT", body, **kw)

    def delete(self, path: str, **kw: Any) -> tuple[int, Any]:
        return self.request(path, "DELETE", **kw)


@pytest.fixture(scope="session")
def client() -> TestClient:
    # raise_server_exceptions=False so a 500 comes back as a response and the
    # "errors never leak" assertions can inspect it.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def delete_account(email: str) -> None:
    with SessionLocal() as session:
        session.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
        session.commit()


def unique_email(prefix: str) -> str:
    return f"{prefix}-{time.time_ns()}@{TEST_EMAIL_DOMAIN}"


@pytest.fixture(scope="module")
def owner_email(request: pytest.FixtureRequest) -> str:
    prefix = request.module.__name__.replace("tests.", "").replace("test_", "")
    email = unique_email(prefix)
    yield email
    delete_account(email)


@pytest.fixture(scope="module")
def api(client: TestClient, owner_email: str) -> Api:
    """A registered, logged-in owner with an empty book."""
    anonymous = Api(client)
    status, body = anonymous.post(
        "/auth/register",
        {"fullName": "Test Owner", "email": owner_email, "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 201, f"could not register test owner: {body}"
    return Api(client, body["data"]["token"])


@pytest.fixture(scope="module")
def anon(client: TestClient) -> Api:
    """An unauthenticated caller."""
    return Api(client)


class PhoneBook:
    """Valid SA phone numbers, one per customer, formatted 3-3-4."""

    def __init__(self) -> None:
        self._counter = 0

    def next(self) -> str:
        self._counter += 1
        digits = f"07{self._counter:08d}"
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"


@pytest.fixture(scope="module")
def phones() -> PhoneBook:
    return PhoneBook()


@pytest.fixture(scope="module")
def new_customer(api: Api, phones: PhoneBook):
    """Fresh customer per call, so one test's balance cannot affect another's."""

    def _create(name: str) -> int:
        status, body = api.post("/customers", {"fullName": name, "phone": phones.next()})
        assert status == 201, f"could not create customer: {body}"
        return body["data"]["id"]

    return _create
