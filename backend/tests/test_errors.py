"""Error handling and the cascade rules.

The contract the frontend relies on: every failure is JSON, carries
`success: false` and a `message` a shop owner can read, and never leaks SQL or
a stack trace.
"""

from __future__ import annotations

from tests.conftest import Api


def test_unknown_api_paths_return_json_not_html(api: Api) -> None:
    status, body = api.get("/does-not-exist")
    assert status == 404
    assert body["success"] is False
    assert body["message"] == "That endpoint does not exist."


def test_an_unknown_api_post_path_also_returns_json(api: Api) -> None:
    status, body = api.post("/nope/at/all", {"anything": 1})
    assert status == 404
    assert body["success"] is False


def test_malformed_json_gets_a_friendly_message(client, api: Api) -> None:
    response = client.post(
        "/api/customers",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api.token}"},
        content="{ not json",
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid request format."


def test_errors_never_leak_sql_or_stack_traces(api: Api) -> None:
    _, body = api.get("/customers/abc")
    lowered = body["message"].lower()
    for leak in ("select", "insert", "psycopg", "postgres", "traceback", "sqlalchemy"):
        assert leak not in lowered


def test_a_failed_constraint_reads_as_a_sentence_not_a_constraint_name(
    api: Api, new_customer
) -> None:
    new_customer("Constraint Message")
    _, body = api.post("/customers", {"fullName": "Same Number", "phone": "071 234 5678"})
    status, duplicate = api.post(
        "/customers", {"fullName": "Same Number Again", "phone": "071 234 5678"}
    )
    assert status == 409
    assert duplicate["message"] == "You already have a customer with that phone number."


def test_every_error_body_carries_success_false(api: Api) -> None:
    for status, body in (
        api.get("/customers/abc"),
        api.get("/customers/99999999"),
        api.get("/does-not-exist"),
        api.post("/customers", {"fullName": "No Phone"}),
    ):
        assert status >= 400
        assert body["success"] is False
        assert isinstance(body["message"], str)
        assert body["message"]


def test_deleting_a_customer_removes_their_transactions_too(api: Api, new_customer) -> None:
    customer_id = new_customer("Cascade Test")

    _, created = api.post(
        f"/customers/{customer_id}/transactions",
        {"type": "CREDIT", "amount": 100, "description": "Goods", "dueDate": "2030-01-01"},
    )
    transaction_id = created["data"]["transaction"]["id"]

    assert api.delete(f"/customers/{customer_id}")[0] == 200
    assert api.get(f"/customers/{customer_id}")[0] == 404
    assert api.get(f"/transactions/{transaction_id}")[0] == 404


def test_security_headers_are_set(client) -> None:
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "same-origin"


def test_the_frontend_is_served_from_the_same_origin(client) -> None:
    response = client.get("/login.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # An unknown page falls back to the landing page rather than a 404.
    assert client.get("/somewhere-else").status_code == 200
