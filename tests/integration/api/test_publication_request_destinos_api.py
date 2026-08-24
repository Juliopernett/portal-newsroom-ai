"""Integration tests: /publication-requests/{id}/destinos and WordPress draft creation.

`get_cms_publisher` is overridden with a fake, in-memory `CMSPublisher` —
no test here ever makes a real network call to WordPress.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agents.ai.fake_provider import FakeAIProvider
from agents.wordpress.client import WordPressCMSPublisher
from app.api.dependencies import get_ai_provider, get_cms_publisher
from app.api.main import app
from config.settings import Settings
from core.ports.ai_provider import AIProviderError
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult


class _FakeCMSPublisher:
    """In-memory CMSPublisher used across this whole test module — implements
    every `CMSPublisher` method (Sprint 2026-08-21 added 3 to the Protocol)
    so `preparar_y_crear_borrador` never hits a real network call."""

    def __init__(
        self,
        resultado: CMSDraftResult | None = None,
        error: Exception | None = None,
        categorias: list[CategoriaCMS] | None = None,
    ) -> None:
        self.resultado = resultado
        self.error = error
        self.categorias = categorias or []
        self.contenido_recibido: dict[str, Any] | None = None
        self.etiquetas_resueltas: list[str] = []
        self.media_subida: list[tuple[str, str, int]] = []

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        if self.error is not None:
            raise self.error
        self.contenido_recibido = content
        assert self.resultado is not None
        return self.resultado

    def listar_categorias(self) -> list[CategoriaCMS]:
        return self.categorias

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        self.etiquetas_resueltas.append(nombre)
        return f"tag-{nombre}"

    def subir_media(self, contenido: bytes, nombre_archivo: str, content_type: str) -> str:
        self.media_subida.append((nombre_archivo, content_type, len(contenido)))
        return "media-1"


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
    assert body["destino"]["wp_post_id"] == "42"
    assert body["destino"]["wp_url"] == "https://www.portalvallenato.com/?p=42"
    assert body["destino"]["estado"] == "pendiente"
    assert body["preparacion_ia_estado"] == "procesado"
    assert body["preparacion_ia_error"] is None


def test_crear_borrador_wordpress_forwards_category_and_tags_to_wordpress(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    fake_cms_publisher.categorias = [CategoriaCMS(id="7", nombre="Noticias")]
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        respuesta_json=(
            '{"titulo": "Titular IA", "entradilla": "Entradilla", '
            '"contenido": "Cuerpo reescrito", "categoria": "Noticias", '
            '"etiquetas": ["vallenato", "lanzamiento"], "slug": "titular-ia"}'
        )
    )
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 200
    assert fake_cms_publisher.contenido_recibido is not None
    assert fake_cms_publisher.contenido_recibido["title"] == "Titular IA"
    assert fake_cms_publisher.contenido_recibido["content"] == "Cuerpo reescrito"
    assert fake_cms_publisher.contenido_recibido["categories"] == ["7"]
    assert fake_cms_publisher.etiquetas_resueltas == ["vallenato", "lanzamiento"]

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["preparacion_ia_estado"] == "procesado"
    assert solicitud["contenido_editorial"] == "Cuerpo reescrito"
    assert solicitud["texto"] == "Anuncio"  # el original nunca se toca


def test_crear_borrador_wordpress_still_creates_draft_when_ai_fails(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    """An AI outage must never block the WordPress integration."""
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        error=AIProviderError("ANTHROPIC_API_KEY no está configurado en .env")
    )
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Anuncio con texto crudo"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["destino"]["wp_post_id"] == "42"
    assert body["preparacion_ia_estado"] == "fallido"
    assert body["preparacion_ia_error"] is not None
    assert fake_cms_publisher.contenido_recibido == {
        "title": "Anuncio con texto crudo",
        "content": "Anuncio con texto crudo",
    }

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["preparacion_ia_estado"] == "fallido"
    assert solicitud["contenido_editorial"] is None
    assert solicitud["texto"] == "Anuncio con texto crudo"


def test_crear_borrador_wordpress_attaches_the_solicitud_featured_image(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"contenido-de-la-foto", "image/jpeg")},
    )
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 200
    assert fake_cms_publisher.media_subida == [
        ("foto.jpg", "image/jpeg", len(b"contenido-de-la-foto"))
    ]
    assert fake_cms_publisher.contenido_recibido is not None
    assert fake_cms_publisher.contenido_recibido["featured_media"] == "media-1"


def test_crear_borrador_wordpress_rolls_back_completely_when_wordpress_fails(
    client: TestClient, fake_cms_publisher: _FakeCMSPublisher
) -> None:
    import requests

    fake_cms_publisher.error = requests.ConnectionError("WordPress no responde")
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Anuncio a reintentar"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )

    assert response.status_code == 502

    # nothing was saved — solicitud and destino are exactly as before,
    # retriable with a single click, no need to re-paste anything
    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["preparacion_ia_estado"] == "pendiente"
    assert solicitud["texto"] == "Anuncio a reintentar"
    destinos = client.get(f"/publication-requests/{solicitud_id}/destinos").json()
    assert destinos[0]["wp_post_id"] is None

    # and a retry (now that WordPress is "back up") succeeds cleanly
    fake_cms_publisher.error = None
    retry = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/crear-borrador-wordpress"
    )
    assert retry.status_code == 200
    assert retry.json()["destino"]["wp_post_id"] == "42"


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


def test_confirmar_publicacion_registers_meta_post_id_when_given(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={
            "url_publicacion": "https://www.facebook.com/reel/1104219988954059/",
            "meta_post_id": "137967556315253_1521505290021833",
        },
    )

    assert response.status_code == 200
    assert response.json()["meta_post_id"] == "137967556315253_1521505290021833"


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


def test_corregir_enlace_replaces_url_publicacion_on_a_published_destino(
    client: TestClient,
) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/wrong"},
    )

    response = client.patch(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["url_publicacion"] == "https://instagram.com/p/correct"
    assert body["estado"] == "publicado"


def test_corregir_enlace_updates_meta_post_id_when_given(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/wrong"},
    )

    response = client.patch(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct", "meta_post_id": "789"},
    )

    assert response.status_code == 200
    assert response.json()["meta_post_id"] == "789"


def test_corregir_enlace_persists(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/wrong"},
    )
    client.patch(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    destinos = client.get(f"/publication-requests/{solicitud_id}/destinos").json()

    assert destinos[0]["url_publicacion"] == "https://instagram.com/p/correct"


def test_corregir_enlace_does_not_reopen_fecha_cierre(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/wrong"},
    )
    fecha_cierre_original = next(
        s for s in client.get("/publication-requests").json() if s["id"] == solicitud_id
    )["fecha_cierre"]

    client.patch(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    solicitud = next(
        s for s in client.get("/publication-requests").json() if s["id"] == solicitud_id
    )
    assert solicitud["fecha_cierre"] == fecha_cierre_original


def test_corregir_enlace_rejects_a_destino_not_yet_publicado(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    response = client.patch(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    assert response.status_code == 422


def test_corregir_enlace_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.patch(
        "/publication-requests/no-existe/destinos/no-existe/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    assert response.status_code == 404


def test_corregir_enlace_returns_404_when_destino_not_found(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.patch(
        f"/publication-requests/{solicitud_id}/destinos/no-existe/corregir-enlace",
        json={"url_publicacion": "https://instagram.com/p/correct"},
    )

    assert response.status_code == 404


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


def test_eliminar_destino_redundante_junto_a_otro_ya_publicado(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    wordpress_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}/confirmar-publicacion",
        json={},
    )
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"})
    facebook_id = client.get(f"/publication-requests/{solicitud_id}/destinos").json()[1]["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{facebook_id}/confirmar-publicacion",
        json={"url_publicacion": "https://facebook.com/post/1"},
    )

    response = client.delete(f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}")

    assert response.status_code == 204
    destinos = client.get(f"/publication-requests/{solicitud_id}/destinos").json()
    assert len(destinos) == 1
    assert destinos[0]["canal"] == "facebook"


def test_eliminar_destino_rejects_when_it_is_the_only_published_one(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    wordpress_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}/confirmar-publicacion",
        json={},
    )

    response = client.delete(f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}")

    assert response.status_code == 422
    assert len(client.get(f"/publication-requests/{solicitud_id}/destinos").json()) == 1


def test_eliminar_destino_no_reabre_fecha_cierre(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]
    wordpress_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}/confirmar-publicacion",
        json={},
    )
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"})
    instagram_id = client.get(f"/publication-requests/{solicitud_id}/destinos").json()[1]["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{instagram_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/abc"},
    )

    client.delete(f"/publication-requests/{solicitud_id}/destinos/{wordpress_id}")

    solicitudes = client.get("/publication-requests").json()
    solicitud = next(s for s in solicitudes if s["id"] == solicitud_id)
    assert solicitud["fecha_cierre"] is not None


def test_eliminar_destino_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.delete("/publication-requests/no-existe/destinos/no-existe")

    assert response.status_code == 404


def test_eliminar_destino_returns_404_when_destino_not_found(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Anuncio"}).json()["id"]

    response = client.delete(f"/publication-requests/{solicitud_id}/destinos/no-existe")

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
