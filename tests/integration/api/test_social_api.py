"""Integration tests: GET /social/posts-recientes."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_posts_recientes_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/social/posts-recientes", params={"canal": "facebook"})

    assert response.status_code == 401


def test_posts_recientes_returns_facebook_posts(client: TestClient) -> None:
    response = client.get("/social/posts-recientes", params={"canal": "facebook"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(post["canal"] == "facebook" for post in body)
    assert all(post["texto"].startswith("[DEMO]") for post in body)


def test_posts_recientes_returns_instagram_posts(client: TestClient) -> None:
    response = client.get("/social/posts-recientes", params={"canal": "instagram"})

    assert response.status_code == 200
    body = response.json()
    assert all(post["canal"] == "instagram" for post in body)


def test_posts_recientes_respects_limite(client: TestClient) -> None:
    response = client.get(
        "/social/posts-recientes", params={"canal": "facebook", "limite": 2}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_posts_recientes_rejects_wordpress(client: TestClient) -> None:
    response = client.get("/social/posts-recientes", params={"canal": "wordpress"})

    assert response.status_code == 422
