"""Unit tests for the PublicationRequest entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.publication_request import (
    EstadoPreparacionIA,
    PublicationRequest,
    PublicationRequestStatus,
)


def _build(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "texto": "Publicar el video del lanzamiento del sencillo el viernes.",
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_create_publication_request_assigns_defaults() -> None:
    solicitud = _build()

    assert solicitud.id
    assert solicitud.pauta_id is None
    assert solicitud.titulo is None
    assert solicitud.estado == PublicationRequestStatus.RECIBIDA
    assert solicitud.prioridad_manual is False
    assert solicitud.observaciones is None
    assert solicitud.fecha_cierre is None
    assert isinstance(solicitud.fecha_recepcion, datetime)


def test_create_publication_request_accepts_explicit_values() -> None:
    fecha_recepcion = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)

    solicitud = _build(
        id="solicitud-1",
        pauta_id="pauta-1",
        fecha_recepcion=fecha_recepcion,
        estado=PublicationRequestStatus.ACEPTADA,
        prioridad_manual=True,
        observaciones="Cliente pidió publicar antes del mediodía",
    )

    assert solicitud.id == "solicitud-1"
    assert solicitud.pauta_id == "pauta-1"
    assert solicitud.fecha_recepcion == fecha_recepcion
    assert solicitud.estado == PublicationRequestStatus.ACEPTADA
    assert solicitud.prioridad_manual is True
    assert solicitud.observaciones == "Cliente pidió publicar antes del mediodía"


def test_create_publication_request_rejects_empty_texto() -> None:
    with pytest.raises(ValueError, match="texto"):
        _build(texto="")


def test_create_publication_request_rejects_empty_string_pauta_id() -> None:
    with pytest.raises(ValueError, match="pauta_id"):
        _build(pauta_id="")


@pytest.mark.parametrize(
    "estado", [PublicationRequestStatus.RECIBIDA, PublicationRequestStatus.CANCELADA]
)
def test_create_publication_request_allows_missing_pauta_id(
    estado: PublicationRequestStatus,
) -> None:
    solicitud = _build(estado=estado, pauta_id=None)

    assert solicitud.pauta_id is None
    assert solicitud.estado == estado


def test_create_publication_request_requires_pauta_id_when_aceptada() -> None:
    with pytest.raises(ValueError, match="pauta_id"):
        _build(estado=PublicationRequestStatus.ACEPTADA, pauta_id=None)


def test_create_publication_request_accepts_pauta_id_when_aceptada() -> None:
    solicitud = _build(estado=PublicationRequestStatus.ACEPTADA, pauta_id="pauta-1")

    assert solicitud.pauta_id == "pauta-1"
    assert solicitud.estado == PublicationRequestStatus.ACEPTADA


def test_publication_request_is_immutable() -> None:
    solicitud = _build()

    with pytest.raises(AttributeError):
        solicitud.estado = PublicationRequestStatus.CANCELADA  # type: ignore[misc]


def test_create_publication_request_accepts_titulo_and_fecha_cierre() -> None:
    fecha_cierre = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)

    solicitud = _build(titulo="Lanzamiento del sencillo", fecha_cierre=fecha_cierre)

    assert solicitud.titulo == "Lanzamiento del sencillo"
    assert solicitud.fecha_cierre == fecha_cierre


def test_create_publication_request_rejects_empty_string_titulo() -> None:
    with pytest.raises(ValueError, match="titulo"):
        _build(titulo="")


def test_create_publication_request_defaults_preparacion_ia_estado_to_pendiente() -> None:
    solicitud = _build()

    assert solicitud.preparacion_ia_estado == EstadoPreparacionIA.PENDIENTE
    assert solicitud.contenido_editorial is None
    assert solicitud.etiquetas_editorial is None
    assert solicitud.preparacion_ia_error is None


def test_create_publication_request_accepts_a_procesado_editorial_result() -> None:
    solicitud = _build(
        contenido_editorial="Cuerpo reescrito por IA",
        titulo_editorial="Titular generado",
        etiquetas_editorial=("vallenato", "lanzamiento"),
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )

    assert solicitud.contenido_editorial == "Cuerpo reescrito por IA"
    assert solicitud.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO


def test_create_publication_request_rejects_procesado_without_contenido_editorial() -> None:
    with pytest.raises(ValueError, match="contenido_editorial"):
        _build(preparacion_ia_estado=EstadoPreparacionIA.PROCESADO)


def test_create_publication_request_rejects_fallido_without_preparacion_ia_error() -> None:
    with pytest.raises(ValueError, match="preparacion_ia_error"):
        _build(preparacion_ia_estado=EstadoPreparacionIA.FALLIDO)


def test_create_publication_request_accepts_a_fallido_editorial_result() -> None:
    solicitud = _build(
        preparacion_ia_estado=EstadoPreparacionIA.FALLIDO,
        preparacion_ia_error="ANTHROPIC_API_KEY no configurado",
    )

    assert solicitud.preparacion_ia_estado == EstadoPreparacionIA.FALLIDO
    assert solicitud.preparacion_ia_error == "ANTHROPIC_API_KEY no configurado"
    assert solicitud.contenido_editorial is None
