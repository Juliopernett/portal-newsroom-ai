"""Unit tests for reporte_service — pure, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime

from core.entities.client import Client, ClientType
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.publication_request import PublicationRequest
from core.services.reporte_service import construir_reporte


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


def _cliente(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def test_construir_reporte_includes_basic_solicitud_fields() -> None:
    solicitud = _solicitud(titulo="Lanzamiento", texto="Texto completo")

    reporte = construir_reporte(solicitud, [], None)

    assert reporte.publication_request_id == solicitud.id
    assert reporte.titulo == "Lanzamiento"
    assert reporte.texto == "Texto completo"
    assert reporte.fecha_recepcion == solicitud.fecha_recepcion


def test_construir_reporte_uses_wp_url_for_wordpress_enlace() -> None:
    destino = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        wp_post_id="42",
        wp_url="https://portalvallenato.com/?p=42",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    reporte = construir_reporte(_solicitud(), [destino], None)

    assert reporte.destinos[0].enlace == "https://portalvallenato.com/?p=42"


def test_construir_reporte_uses_url_publicacion_for_social_enlace() -> None:
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        url_publicacion="https://instagram.com/p/abc",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    reporte = construir_reporte(_solicitud(), [destino], None)

    assert reporte.destinos[0].enlace == "https://instagram.com/p/abc"


def test_construir_reporte_preserves_destino_order_and_fields() -> None:
    wordpress = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PENDIENTE,
    )
    instagram = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.FALLIDO,
        ultimo_error="No se pudo confirmar",
    )

    reporte = construir_reporte(_solicitud(), [wordpress, instagram], None)

    assert [d.canal for d in reporte.destinos] == [
        CanalPublicacion.WORDPRESS,
        CanalPublicacion.INSTAGRAM,
    ]
    assert reporte.destinos[1].ultimo_error == "No se pudo confirmar"


def test_construir_reporte_cliente_nombre_from_cliente() -> None:
    cliente = _cliente(nombre="Andrés Ariza")

    reporte = construir_reporte(_solicitud(), [], cliente)

    assert reporte.cliente_nombre == "Andrés Ariza"


def test_construir_reporte_cliente_nombre_is_none_without_cliente() -> None:
    reporte = construir_reporte(_solicitud(), [], None)

    assert reporte.cliente_nombre is None


def test_construir_reporte_completa_is_false_with_no_destinos() -> None:
    reporte = construir_reporte(_solicitud(), [], None)

    assert reporte.completa is False
    assert reporte.pauta_consumida is False


def test_construir_reporte_completa_true_and_pauta_consumida_true_when_linked() -> None:
    destino = _destino(
        estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC)
    )
    solicitud = _solicitud(pauta_id="pauta-1")

    reporte = construir_reporte(solicitud, [destino], None)

    assert reporte.completa is True
    assert reporte.pauta_consumida is True


def test_construir_reporte_completa_true_but_pauta_consumida_false_without_pauta() -> None:
    """Instagram-only, never linked to a Pauta (Sprint 4A, Incremento 4/5) —
    complete, but nothing was consumed because there is no Pauta at all."""
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        url_publicacion="https://instagram.com/p/abc",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )
    solicitud = _solicitud(pauta_id=None)

    reporte = construir_reporte(solicitud, [destino], None)

    assert reporte.completa is True
    assert reporte.pauta_consumida is False


def test_construir_reporte_not_complete_with_a_pending_destino() -> None:
    destino = _destino(estado=EstadoDestino.PENDIENTE)
    solicitud = _solicitud(pauta_id="pauta-1")

    reporte = construir_reporte(solicitud, [destino], None)

    assert reporte.completa is False
    assert reporte.pauta_consumida is False
