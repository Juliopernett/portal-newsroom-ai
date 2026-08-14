"""Unit tests for aceptar and link_pauta."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.publication_request_service import (
    aceptar,
    cancelar_solicitud,
    cerrar_si_completa,
    edit_solicitud,
    link_pauta,
)


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "pauta_id": "pauta-1",
        "texto": "Solicitud de ejemplo",
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_aceptar_transitions_status_to_aceptada() -> None:
    solicitud = _solicitud()

    resultado = aceptar(solicitud)

    assert resultado.estado == PublicationRequestStatus.ACEPTADA


def test_aceptar_does_not_mutate_the_original() -> None:
    solicitud = _solicitud()

    aceptar(solicitud)

    assert solicitud.estado == PublicationRequestStatus.RECIBIDA


def test_aceptar_preserves_the_rest_of_the_fields() -> None:
    solicitud = _solicitud(texto="No cambiar este texto", prioridad_manual=True)

    resultado = aceptar(solicitud)

    assert resultado.id == solicitud.id
    assert resultado.pauta_id == solicitud.pauta_id
    assert resultado.texto == "No cambiar este texto"
    assert resultado.prioridad_manual is True


def test_aceptar_raises_when_pauta_id_is_missing() -> None:
    solicitud = _solicitud(pauta_id=None)

    with pytest.raises(ValueError, match="pauta_id"):
        aceptar(solicitud)


def test_link_pauta_sets_the_pauta_id() -> None:
    solicitud = _solicitud(pauta_id=None)

    resultado = link_pauta(solicitud, "pauta-nueva")

    assert resultado.pauta_id == "pauta-nueva"


def test_link_pauta_does_not_mutate_the_original() -> None:
    solicitud = _solicitud(pauta_id=None)

    link_pauta(solicitud, "pauta-nueva")

    assert solicitud.pauta_id is None


def test_link_pauta_does_not_change_estado() -> None:
    solicitud = _solicitud(pauta_id=None)

    resultado = link_pauta(solicitud, "pauta-nueva")

    assert resultado.estado == PublicationRequestStatus.RECIBIDA


def test_link_pauta_can_replace_an_existing_pauta_id() -> None:
    solicitud = _solicitud(pauta_id="pauta-vieja")

    resultado = link_pauta(solicitud, "pauta-nueva")

    assert resultado.pauta_id == "pauta-nueva"


def test_link_pauta_rejects_an_empty_pauta_id() -> None:
    solicitud = _solicitud(pauta_id=None)

    with pytest.raises(ValueError, match="pauta_id"):
        link_pauta(solicitud, "")


def test_edit_solicitud_updates_texto() -> None:
    solicitud = _solicitud(texto="Texto original")

    resultado = edit_solicitud(solicitud, texto="Texto corregido")

    assert resultado.texto == "Texto corregido"


def test_edit_solicitud_updates_titulo() -> None:
    solicitud = _solicitud(titulo="Titulo original")

    resultado = edit_solicitud(solicitud, titulo="Titulo corregido")

    assert resultado.titulo == "Titulo corregido"


def test_edit_solicitud_leaves_titulo_untouched_when_not_provided() -> None:
    solicitud = _solicitud(titulo="Titulo original")

    resultado = edit_solicitud(solicitud, texto="Otro texto")

    assert resultado.titulo == "Titulo original"


def test_edit_solicitud_updates_prioridad_manual() -> None:
    solicitud = _solicitud(prioridad_manual=False)

    resultado = edit_solicitud(solicitud, prioridad_manual=True)

    assert resultado.prioridad_manual is True


def test_edit_solicitud_leaves_unset_fields_untouched() -> None:
    solicitud = _solicitud(texto="Texto original", prioridad_manual=True)

    resultado = edit_solicitud(solicitud, prioridad_manual=False)

    assert resultado.texto == "Texto original"
    assert resultado.prioridad_manual is False


def test_edit_solicitud_does_not_mutate_the_original() -> None:
    solicitud = _solicitud(texto="Texto original")

    edit_solicitud(solicitud, texto="Texto corregido")

    assert solicitud.texto == "Texto original"


def test_edit_solicitud_rejects_an_empty_texto() -> None:
    solicitud = _solicitud()

    with pytest.raises(ValueError, match="texto"):
        edit_solicitud(solicitud, texto="")


def test_edit_solicitud_rejects_editing_an_aceptada_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.ACEPTADA)

    with pytest.raises(ValueError, match="aceptada"):
        edit_solicitud(solicitud, texto="Intento tardío")


def test_edit_solicitud_rejects_editing_a_cancelled_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.CANCELADA, pauta_id=None)

    with pytest.raises(ValueError, match="cancelada"):
        edit_solicitud(solicitud, texto="Intento tardío")


def test_cancelar_solicitud_transitions_status_to_cancelada() -> None:
    solicitud = _solicitud()

    resultado = cancelar_solicitud(solicitud)

    assert resultado.estado == PublicationRequestStatus.CANCELADA


def test_cancelar_solicitud_does_not_mutate_the_original() -> None:
    solicitud = _solicitud()

    cancelar_solicitud(solicitud)

    assert solicitud.estado == PublicationRequestStatus.RECIBIDA


def test_cancelar_solicitud_preserves_the_rest_of_the_fields() -> None:
    solicitud = _solicitud(texto="No cambiar este texto", prioridad_manual=True)

    resultado = cancelar_solicitud(solicitud)

    assert resultado.id == solicitud.id
    assert resultado.pauta_id == solicitud.pauta_id
    assert resultado.texto == "No cambiar este texto"
    assert resultado.prioridad_manual is True


def test_cancelar_solicitud_rejects_an_already_aceptada_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.ACEPTADA)

    with pytest.raises(ValueError, match="aceptada"):
        cancelar_solicitud(solicitud)


def test_cancelar_solicitud_rejects_an_already_cancelled_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.CANCELADA, pauta_id=None)

    with pytest.raises(ValueError, match="cancelada"):
        cancelar_solicitud(solicitud)


def _destino(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "canal": CanalPublicacion.WORDPRESS,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_cerrar_si_completa_sets_fecha_cierre_when_complete() -> None:
    solicitud = _solicitud()
    destinos = [
        _destino(estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC))
    ]

    resultado = cerrar_si_completa(solicitud, destinos)

    assert resultado.fecha_cierre is not None


def test_cerrar_si_completa_accepts_explicit_fecha_cierre() -> None:
    solicitud = _solicitud()
    destinos = [
        _destino(estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC))
    ]
    fecha_cierre = datetime(2026, 8, 6, 15, 0, tzinfo=UTC)

    resultado = cerrar_si_completa(solicitud, destinos, fecha_cierre=fecha_cierre)

    assert resultado.fecha_cierre == fecha_cierre


def test_cerrar_si_completa_leaves_solicitud_unchanged_when_not_complete() -> None:
    solicitud = _solicitud()
    destinos = [_destino(estado=EstadoDestino.PENDIENTE)]

    resultado = cerrar_si_completa(solicitud, destinos)

    assert resultado.fecha_cierre is None


def test_cerrar_si_completa_does_not_mutate_the_original() -> None:
    solicitud = _solicitud()
    destinos = [
        _destino(estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC))
    ]

    cerrar_si_completa(solicitud, destinos)

    assert solicitud.fecha_cierre is None


def test_cerrar_si_completa_is_idempotent_once_already_closed() -> None:
    fecha_original = datetime(2026, 8, 6, 9, 0, tzinfo=UTC)
    solicitud = _solicitud(fecha_cierre=fecha_original)
    destinos = [_destino(estado=EstadoDestino.PENDIENTE)]

    resultado = cerrar_si_completa(
        solicitud, destinos, fecha_cierre=datetime(2026, 8, 7, tzinfo=UTC)
    )

    assert resultado.fecha_cierre == fecha_original
