"""Integration tests: /publication-requests/{id}/destinos and WordPress draft creation.

`get_cms_publisher` is overridden with a fake, in-memory `CMSPublisher` —
no test here ever makes a real network call to WordPress.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agents.wordpress.client import WordPressCMSPublisher
from app.api.dependencies import get_cms_publisher
from app.api.main import app
from config.settings import Settings
from core.ports.cms_publisher import CMSDraftResult


class _FakeCMSPublisher:
    def __init__(
        self, resultado: CMSDraftResult | None = None, error: Exception | None = None
    ) -> None:
        self.resultado = resultado
        self.error = error

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        if self.error is not None:
            raise self.error
        assert self.resultado is not None
        return self.resultado


@pytest.fixture
def fake_cms_publisher() -> Iterator[_FakeCMSPublisher]:
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="42", url="https://www.portalvallenato.com/?p=42")
    )
    app.dependency_overrides[get_cms_publisher] = lambda: publisher
    yield publisher
    del app.dependency_overrides[get_cms_publisher]


def test_create_destino_for_a_publication_request(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["publication_request_id"] == solicitud_id
    assert body["canal"] == "wordpress"
    assert body["estado"] == "pendiente"


def test_create_destino_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.post("/publication-requests/no-existe/destinos", json={"canal": "wordpress"})

    assert response.status_code == 404


def test_create_destino_rejects_an_invalid_canal(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "tiktok"}
    )

    assert response.status_code == 422


def test_list_destinos_returns_every_destino_for_the_solicitud(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"})
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"})

    response = client.get(f"/publication-requests/{solicitud_id}/destinos")

    assert response.status_code == 200
    canales = {d["canal"] for d in response.json()}
    assert canales == {"wordpress", "instagram"}


def test_list_destinos_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.get("/publication-requests/no-existe/destinos")

    assert response.status_code == 404


def test_crear_borrador_wordpress_attaches_post_id_and_url(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Anuncio", "titulo": "Titulo"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["wp_post_id"] == "42"
    assert body["wp_url"] == "https://www.portalvallenato.com/?p=42"
    assert body["estado"] == "pendiente"


def test_publish_reuses_an_existing_wordpress_destino_from_crear_borrador(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    """A solicitud that already went through crear-borrador-wordpress (Increment 3)
    and then gets the old one-click "Publicar" (Increment 4 compatibility flow)
    must reuse that WordPress destino instead of creating a duplicate."""
    client_id = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    ).json()["id"]
    pauta_id = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 10,
            "valor_pagado": "500000.00",
            "fecha_pago": "2026-07-30",
        },
    ).json()["id"]
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    response = client.post(f"/publication-requests/{solicitud_id}/publish")

    assert response.status_code == 200
    assert response.json()["estado"] == "aceptada"

    destinos = client.get(f"/publication-requests/{solicitud_id}/destinos").json()
    assert len(destinos) == 1
    assert destinos[0]["id"] == destino_id
    assert destinos[0]["estado"] == "publicado"
    assert destinos[0]["wp_post_id"] == "42"


def test_crear_borrador_wordpress_returns_404_when_solicitud_not_found(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    response = client.post(
        "/publication-requests/no-existe/destinos/no-existe/crear-borrador-wordpress"
    )

    assert response.status_code == 404


def test_crear_borrador_wordpress_returns_404_when_destino_not_found(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/no-existe/crear-borrador-wordpress"
    )

    assert response.status_code == 404


def test_crear_borrador_wordpress_rejects_a_non_wordpress_destino(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 422


def test_confirmar_publicacion_registers_url_for_instagram(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/abc123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "publicado"
    assert body["url_publicacion"] == "https://instagram.com/p/abc123"
    assert body["registrado_por_user_id"] is not None
    assert body["fecha_publicacion"] is not None


def test_confirmar_publicacion_rejects_instagram_without_url(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={},
    )

    assert response.status_code == 422


def test_confirmar_publicacion_accepts_wordpress_without_url(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "publicado"


def test_confirmar_publicacion_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.post(
        "/publication-requests/no-existe/destinos/no-existe/confirmar-publicacion", json={}
    )

    assert response.status_code == 404


def test_confirmar_publicacion_returns_404_when_destino_not_found(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/no-existe/confirmar-publicacion", json={}
    )

    assert response.status_code == 404


def test_confirmar_publicacion_sets_fecha_cierre_once_solicitud_is_complete(
    client: TestClient,
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={},
    )

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["fecha_cierre"] is not None


def test_confirmar_publicacion_does_not_close_while_another_destino_is_pending(
    client: TestClient,
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    wordpress_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"})

    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}/confirmar-publicacion",
        json={},
    )

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["fecha_cierre"] is None


def test_cancelar_destino_pendiente(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    response = client.post(f"/publication-requests/{solicitud_id}/destinos/{destino_id}/cancelar")

    assert response.status_code == 200
    assert response.json()["estado"] == "cancelado"


def test_cancelar_the_last_pending_destino_completes_the_solicitud(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    wordpress_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    instagram_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}/confirmar-publicacion",
        json={},
    )
    client.post(f"/publication-requests/{solicitud_id}/destinos/{instagram_id}/cancelar")

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["fecha_cierre"] is not None


def test_cancelar_rejects_an_already_publicado_destino(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={},
    )

    response = client.post(f"/publication-requests/{solicitud_id}/destinos/{destino_id}/cancelar")

    assert response.status_code == 422


def test_cancelar_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.post("/publication-requests/no-existe/destinos/no-existe/cancelar")

    assert response.status_code == 404


def test_cancelar_returns_404_when_destino_not_found(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.post(f"/publication-requests/{solicitud_id}/destinos/no-existe/cancelar")

    assert response.status_code == 404


def test_crear_borrador_wordpress_returns_503_when_not_configured(client: TestClient) -> None:
    """Overrides get_cms_publisher with an explicitly unconfigured Settings —
    deliberately never reads the real get_settings()/.env here. This suite
    must never depend on whatever WORDPRESS_* values happen to be in a
    developer's local .env, or a test run could make a real network call
    against a real production WordPress site using real credentials."""

    def _unconfigured_cms_publisher() -> WordPressCMSPublisher:
        return WordPressCMSPublisher(
            Settings(wordpress_site_url=None, wordpress_username=None, wordpress_app_password=None)
        )

    app.dependency_overrides[get_cms_publisher] = _unconfigured_cms_publisher
    try:
        solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
        destino_id = client.post(
            f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
        ).json()["id"]

        response = client.post(
            f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
        )

        assert response.status_code == 503
    finally:
        del app.dependency_overrides[get_cms_publisher]
