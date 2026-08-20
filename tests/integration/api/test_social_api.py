"""Integration tests: GET /social/posts-recientes."""

from __future__ import annotations

from datetime import UTC, datetime

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


def test_posts_recientes_coincidencia_is_none_without_context(client: TestClient) -> None:
    response = client.get("/social/posts-recientes", params={"canal": "facebook"})

    body = response.json()
    assert all(post["coincidencia"] is None for post in body)


def test_posts_recientes_includes_coincidencia_when_context_given(client: TestClient) -> None:
    response = client.get(
        "/social/posts-recientes",
        params={
            "canal": "facebook",
            "solicitud_texto": "cualquier cosa",
            "solicitud_fecha_recepcion": datetime.now(UTC).isoformat(),
        },
    )

    body = response.json()
    assert len(body) > 0
    assert all(post["coincidencia"] is not None for post in body)


def test_posts_recientes_sorts_best_text_match_first(client: TestClient) -> None:
    """El texto exacto de uno de los posts falsos (ver
    agents/meta_social/fake_reader.py) debe ganarle a los demás en el
    orden, aunque no sea el más reciente."""
    response = client.get(
        "/social/posts-recientes",
        params={
            "canal": "facebook",
            "solicitud_texto": "Ya disponible el video oficial Corre a verlo en YouTube",
            "solicitud_fecha_recepcion": datetime.now(UTC).isoformat(),
        },
    )

    body = response.json()
    assert "video oficial" in body[0]["texto"]


def test_posts_recientes_marks_ya_relacionada_when_meta_post_id_is_used(
    client: TestClient,
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={
            "url_publicacion": "https://www.facebook.com/demo/facebook-0",
            "meta_post_id": "demo-facebook-0",
        },
    )

    response = client.get("/social/posts-recientes", params={"canal": "facebook"})

    body = response.json()
    relacionado = next(post for post in body if post["id"] == "demo-facebook-0")
    otro = next(post for post in body if post["id"] != "demo-facebook-0")
    assert relacionado["ya_relacionada"] is True
    assert otro["ya_relacionada"] is False
