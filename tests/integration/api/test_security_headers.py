"""Integration tests: baseline security headers (security audit 2026-08-20, M3)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_every_response_carries_the_baseline_security_headers(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/auth/me")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"


def test_security_headers_are_present_even_on_an_authenticated_response(
    client: TestClient,
) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
