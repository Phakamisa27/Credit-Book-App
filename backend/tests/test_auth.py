"""Registration, login, password hashing, and protected routes."""

from __future__ import annotations

import pytest

from tests.conftest import TEST_PASSWORD, Api, delete_account, unique_email

# One account is registered by these tests and reused across them, in order.
STATE: dict[str, str] = {}


@pytest.fixture(scope="module")
def email() -> str:
    address = unique_email("auth")
    yield address
    delete_account(address)


def test_rejects_registration_with_a_short_password(anon: Api, email: str) -> None:
    status, body = anon.post(
        "/auth/register",
        {"fullName": "Test", "email": f"x-{email}", "password": "short"},
        auth=False,
    )
    assert status == 400
    assert body["success"] is False
    assert "8 characters" in body["message"]


def test_rejects_registration_with_an_invalid_email(anon: Api) -> None:
    status, _ = anon.post(
        "/auth/register",
        {"fullName": "Test", "email": "not-an-email", "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 400


def test_registers_and_returns_a_token(anon: Api, email: str) -> None:
    status, body = anon.post(
        "/auth/register",
        {
            "fullName": "Test Owner",
            "email": email,
            "password": TEST_PASSWORD,
            "businessName": "Test Shop",
        },
        auth=False,
    )
    assert status == 201
    assert body["data"]["token"]
    assert body["data"]["user"]["email"] == email
    assert body["data"]["user"]["businessName"] == "Test Shop"
    # The hash must never leave the server.
    assert "passwordHash" not in body["data"]["user"]
    assert "password_hash" not in body["data"]["user"]
    STATE["token"] = body["data"]["token"]


def test_refuses_a_duplicate_email(anon: Api, email: str) -> None:
    status, _ = anon.post(
        "/auth/register",
        {"fullName": "Test", "email": email, "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 409


def test_rejects_a_wrong_password_without_revealing_which_field_was_wrong(
    anon: Api, email: str
) -> None:
    status, body = anon.post(
        "/auth/login", {"email": email, "password": "WrongPassword123"}, auth=False
    )
    assert status == 401
    assert body["message"] == "Incorrect email or password."


def test_gives_an_unknown_email_the_same_message_as_a_wrong_password(anon: Api) -> None:
    status, body = anon.post(
        "/auth/login",
        {"email": "nobody@creditbook.test", "password": TEST_PASSWORD},
        auth=False,
    )
    assert status == 401
    assert body["message"] == "Incorrect email or password."


def test_logs_in_with_correct_credentials(anon: Api, email: str) -> None:
    status, body = anon.post("/auth/login", {"email": email, "password": TEST_PASSWORD}, auth=False)
    assert status == 200
    assert body["data"]["token"]
    STATE["token"] = body["data"]["token"]


def test_blocks_protected_routes_without_a_token(anon: Api) -> None:
    status, body = anon.get("/customers", auth=False)
    assert status == 401
    assert body["message"] == "Please log in to continue."


def test_blocks_protected_routes_with_a_bad_token(client) -> None:
    response = client.get("/api/customers", headers={"Authorization": "Bearer not.a.real.token"})
    assert response.status_code == 401


def test_blocks_protected_routes_with_a_non_bearer_scheme(client) -> None:
    response = client.get("/api/customers", headers={"Authorization": "Basic abcdef"})
    assert response.status_code == 401


def test_returns_the_signed_in_account(anon: Api, email: str) -> None:
    authed = Api(anon.client, STATE["token"])
    status, body = authed.get("/auth/me")
    assert status == 200
    assert body["data"]["email"] == email
    assert "passwordHash" not in body["data"]


def test_updates_the_business_profile(anon: Api) -> None:
    authed = Api(anon.client, STATE["token"])
    status, body = authed.patch("/auth/me", {"businessName": "Corner Spaza"})
    assert status == 200
    assert body["data"]["businessName"] == "Corner Spaza"


def test_status_reports_that_an_account_exists(anon: Api) -> None:
    status, body = anon.get("/auth/status", auth=False)
    assert status == 200
    assert body["data"]["accountExists"] is True


def test_change_password_requires_the_current_one(anon: Api) -> None:
    authed = Api(anon.client, STATE["token"])
    status, body = authed.post(
        "/auth/change-password",
        {"currentPassword": "NotMyPassword", "newPassword": "BrandNewPassword1"},
    )
    assert status == 400
    assert "current password is incorrect" in body["message"]


def test_change_password_then_log_in_with_the_new_one(anon: Api, email: str) -> None:
    authed = Api(anon.client, STATE["token"])
    new_password = "BrandNewPassword1"

    status, _ = authed.post(
        "/auth/change-password",
        {"currentPassword": TEST_PASSWORD, "newPassword": new_password},
    )
    assert status == 200

    # The old password no longer works…
    status, _ = anon.post("/auth/login", {"email": email, "password": TEST_PASSWORD}, auth=False)
    assert status == 401

    # …and the new one does.
    status, body = anon.post("/auth/login", {"email": email, "password": new_password}, auth=False)
    assert status == 200
    STATE["token"] = body["data"]["token"]


def test_logout_succeeds_and_leaves_the_token_to_the_client(anon: Api) -> None:
    authed = Api(anon.client, STATE["token"])
    status, body = authed.post("/auth/logout")
    assert status == 200
    assert body["data"]["message"] == "Logged out."


def test_password_is_stored_hashed_not_in_plaintext(email: str) -> None:
    from sqlalchemy import text

    from app.db.session import SessionLocal

    with SessionLocal() as session:
        stored = session.execute(
            text("SELECT password_hash FROM users WHERE email = :email"), {"email": email}
        ).scalar_one()

    assert stored.startswith("$2")
    assert "BrandNewPassword1" not in stored
    assert len(stored) >= 59
