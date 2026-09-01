"""Health check."""

from __future__ import annotations

from tests.conftest import Api


def test_responds_without_auth(anon: Api) -> None:
    status, body = anon.get("/health", auth=False)
    assert status == 200
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
