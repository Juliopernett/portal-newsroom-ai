"""Integration tests: the React frontend (`frontend/dist`) is served for
browser navigations, while a client route that shares its exact path with
an API router prefix (e.g. `/gastos`) still reaches the real router for a
non-navigation request — see `app.api.main.serve_frontend`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api.main as main_module


@pytest.fixture(autouse=True)
def _fake_frontend_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the app at a throwaway built frontend, so these tests don't
    depend on `npm run build` having been run first."""
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><title>Portal Vallenato Newsroom</title>")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", tmp_path)
    monkeypatch.setattr(main_module, "FRONTEND_INDEX", index)
    return tmp_path


def test_root_serves_the_frontend_for_a_browser_navigation(client: TestClient) -> None:
    response = client.get("/", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "Portal Vallenato" in response.text


def test_root_is_not_served_without_a_browser_accept_header(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/", headers={"Accept": "application/json"})

    assert response.status_code == 404


def test_a_built_static_file_is_served_directly(
    client: TestClient, _fake_frontend_build: Path
) -> None:
    (_fake_frontend_build / "favicon.svg").write_text("<svg></svg>")

    response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.text == "<svg></svg>"


def test_client_route_colliding_with_an_api_prefix_still_hits_the_api(
    client: TestClient,
) -> None:
    """`/gastos` is both a React Router page and `GET /gastos` (list
    gastos) — a real API call (no `text/html` Accept) must reach the
    router, not the frontend shell."""
    response = client.get("/gastos", headers={"Accept": "application/json"})

    assert response.status_code == 200
    assert response.json() == []


def test_client_route_colliding_with_an_api_prefix_serves_the_frontend_on_page_load(
    client: TestClient,
) -> None:
    response = client.get("/gastos", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "Portal Vallenato" in response.text


def test_publication_requests_never_falls_back_to_the_frontend(
    client: TestClient,
) -> None:
    """Unlike `/gastos`, `/publication-requests` isn't a client route at
    all (the SPA page is `/solicitudes`) — it must always reach the API,
    even for a `target="_blank"` media-download-style navigation."""
    response = client.get("/publication-requests", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert response.json() == []
