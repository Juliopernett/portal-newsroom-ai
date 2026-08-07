"""Unit tests for wordpress_publication_service — no network, fake CMSPublisher."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.publication_request import PublicationRequest
from core.ports.cms_publisher import CMSDraftResult
from core.services.wordpress_publication_service import (
    construir_contenido_wordpress,
    crear_borrador,
)


class _FakeCMSPublisher:
    """In-memory CMSPublisher — records the content it received, no network."""

    def __init__(self, resultado: CMSDraftResult) -> None:
        self.resultado = resultado
        self.contenido_recibido: dict[str, Any] | None = None

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        self.contenido_recibido = content
        return self.resultado


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {"texto": "Anuncio de nueva canción"}
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def _destino(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "canal": CanalPublicacion.WORDPRESS,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_construir_contenido_uses_titulo_when_present() -> None:
    solicitud = _solicitud(titulo="Lanzamiento del sencillo", texto="Texto largo del comunicado")

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido == {
        "title": "Lanzamiento del sencillo",
        "content": "Texto largo del comunicado",
    }


def test_construir_contenido_falls_back_to_texto_prefix_when_no_titulo() -> None:
    texto_largo = "x" * 100
    solicitud = _solicitud(texto=texto_largo)

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido["title"] == texto_largo[:60]
    assert contenido["content"] == texto_largo


def test_crear_borrador_attaches_post_id_and_url() -> None:
    solicitud = _solicitud(titulo="Titulo")
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="42", url="https://example.com/?p=42"))

    resultado = crear_borrador(destino, solicitud, publisher)

    assert resultado.wp_post_id == "42"
    assert resultado.wp_url == "https://example.com/?p=42"


def test_crear_borrador_keeps_estado_pendiente() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    resultado = crear_borrador(destino, solicitud, publisher)

    assert resultado.estado == EstadoDestino.PENDIENTE


def test_crear_borrador_does_not_mutate_the_original_destino() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    crear_borrador(destino, solicitud, publisher)

    assert destino.wp_post_id is None


def test_crear_borrador_passes_built_content_to_the_publisher() -> None:
    solicitud = _solicitud(titulo="Titulo", texto="Cuerpo")
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    crear_borrador(destino, solicitud, publisher)

    assert publisher.contenido_recibido == {"title": "Titulo", "content": "Cuerpo"}


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_crear_borrador_rejects_non_wordpress_canal(canal: CanalPublicacion) -> None:
    solicitud = _solicitud()
    destino = _destino(canal=canal)
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="wordpress"):
        crear_borrador(destino, solicitud, publisher)


def test_crear_borrador_rejects_a_cancelado_destino() -> None:
    solicitud = _solicitud()
    destino = _destino(estado=EstadoDestino.CANCELADO)
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="terminal"):
        crear_borrador(destino, solicitud, publisher)


def test_crear_borrador_rejects_a_publicado_destino() -> None:
    solicitud = _solicitud()
    destino = _destino(
        estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC)
    )
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="terminal"):
        crear_borrador(destino, solicitud, publisher)
