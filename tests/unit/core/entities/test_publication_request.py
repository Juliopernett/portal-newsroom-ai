"""Unit tests for the PublicationRequest entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.publication_request import PublicationRequest, PublicationRequestStatus


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
    assert solicitud.estado == PublicationRequestStatus.RECIBIDA
    assert solicitud.prioridad_manual is False
    assert solicitud.observaciones is None
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


@pytest.mark.parametrize(
    "estado", [PublicationRequestStatus.ACEPTADA, PublicationRequestStatus.PUBLICADA]
)
def test_create_publication_request_requires_pauta_id(estado: PublicationRequestStatus) -> None:
    with pytest.raises(ValueError, match="pauta_id"):
        _build(estado=estado, pauta_id=None)


@pytest.mark.parametrize(
    "estado", [PublicationRequestStatus.ACEPTADA, PublicationRequestStatus.PUBLICADA]
)
def test_create_publication_request_accepts_pauta_id_for_estados_that_require_it(
    estado: PublicationRequestStatus,
) -> None:
    solicitud = _build(estado=estado, pauta_id="pauta-1")

    assert solicitud.pauta_id == "pauta-1"
    assert solicitud.estado == estado


def test_publication_request_is_immutable() -> None:
    solicitud = _build()

    with pytest.raises(AttributeError):
        solicitud.estado = PublicationRequestStatus.PUBLICADA  # type: ignore[misc]
