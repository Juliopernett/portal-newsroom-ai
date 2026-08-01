"""Integration tests: the static UI is served and `/` redirects to it."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_redirects_to_the_ui(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/ui/"


def test_ui_index_is_served(client: TestClient) -> None:
    response = client.get("/ui/")

    assert response.status_code == 200
    assert "Portal Vallenato" in response.text
