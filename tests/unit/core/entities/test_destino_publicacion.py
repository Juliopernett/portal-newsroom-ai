"""Unit tests for the DestinoPublicacion entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino


def _build(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "canal": CanalPublicacion.WORDPRESS,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_create_destino_assigns_defaults() -> None:
    destino = _build()

    assert destino.id
    assert destino.publication_request_id == "solicitud-1"
    assert destino.canal == CanalPublicacion.WORDPRESS
    assert destino.estado == EstadoDestino.PENDIENTE
    assert destino.wp_post_id is None
    assert destino.wp_url is None
    assert destino.url_publicacion is None
    assert destino.meta_post_id is None
    assert destino.registrado_por_user_id is None
    assert destino.fecha_publicacion is None
    assert destino.ultimo_error is None


def test_create_destino_rejects_empty_publication_request_id() -> None:
    with pytest.raises(ValueError, match="publication_request_id"):
        _build(publication_request_id="")


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_wp_fields_rejected_outside_wordpress(canal: CanalPublicacion) -> None:
    with pytest.raises(ValueError, match="wp_post_id"):
        _build(canal=canal, wp_post_id="123")


def test_url_publicacion_rejected_for_wordpress() -> None:
    with pytest.raises(ValueError, match="url_publicacion"):
        _build(canal=CanalPublicacion.WORDPRESS, url_publicacion="https://facebook.com/post/1")


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_url_publicacion_accepted_for_social_channels(canal: CanalPublicacion) -> None:
    destino = _build(
        canal=canal,
        estado=EstadoDestino.PUBLICADO,
        url_publicacion="https://example.com/post/1",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert destino.url_publicacion == "https://example.com/post/1"


def test_meta_post_id_rejected_for_wordpress() -> None:
    with pytest.raises(ValueError, match="meta_post_id"):
        _build(canal=CanalPublicacion.WORDPRESS, meta_post_id="123_456")


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_meta_post_id_accepted_for_social_channels(canal: CanalPublicacion) -> None:
    destino = _build(
        canal=canal,
        estado=EstadoDestino.PUBLICADO,
        url_publicacion="https://example.com/post/1",
        meta_post_id="123_456",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert destino.meta_post_id == "123_456"


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_publicado_requires_url_publicacion_for_social_channels(canal: CanalPublicacion) -> None:
    with pytest.raises(ValueError, match="url_publicacion"):
        _build(
            canal=canal,
            estado=EstadoDestino.PUBLICADO,
            fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        )


def test_wordpress_fields_accepted_for_wordpress() -> None:
    destino = _build(
        wp_post_id="42",
        wp_url="https://portalvallenato.com/?p=42",
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert destino.wp_post_id == "42"
    assert destino.wp_url == "https://portalvallenato.com/?p=42"


def test_publicado_requires_fecha_publicacion() -> None:
    with pytest.raises(ValueError, match="fecha_publicacion"):
        _build(estado=EstadoDestino.PUBLICADO)


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        (EstadoDestino.PENDIENTE, False),
        (EstadoDestino.FALLIDO, False),
        (EstadoDestino.PUBLICADO, True),
        (EstadoDestino.CANCELADO, True),
    ],
)
def test_es_terminal(estado: EstadoDestino, esperado: bool) -> None:
    fecha_publicacion = (
        datetime(2026, 8, 6, tzinfo=UTC) if estado == EstadoDestino.PUBLICADO else None
    )

    destino = _build(estado=estado, fecha_publicacion=fecha_publicacion)

    assert destino.es_terminal is esperado


def test_destino_is_immutable() -> None:
    destino = _build()

    with pytest.raises(AttributeError):
        destino.estado = EstadoDestino.PUBLICADO  # type: ignore[misc]
