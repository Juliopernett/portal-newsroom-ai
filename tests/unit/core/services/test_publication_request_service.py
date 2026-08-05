"""Unit tests for mark_as_published and link_pauta."""

from __future__ import annotations

import pytest

from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.publication_request_service import edit_solicitud, link_pauta, mark_as_published


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "pauta_id": "pauta-1",
        "texto": "Solicitud de ejemplo",
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_mark_as_published_transitions_status_to_publicada() -> None:
    solicitud = _solicitud()

    resultado = mark_as_published(solicitud)

    assert resultado.estado == PublicationRequestStatus.PUBLICADA


def test_mark_as_published_does_not_mutate_the_original() -> None:
    solicitud = _solicitud()

    mark_as_published(solicitud)

    assert solicitud.estado == PublicationRequestStatus.RECIBIDA


def test_mark_as_published_preserves_the_rest_of_the_fields() -> None:
    solicitud = _solicitud(texto="No cambiar este texto", prioridad_manual=True)

    resultado = mark_as_published(solicitud)

    assert resultado.id == solicitud.id
    assert resultado.pauta_id == solicitud.pauta_id
    assert resultado.texto == "No cambiar este texto"
    assert resultado.prioridad_manual is True


def test_mark_as_published_raises_when_pauta_id_is_missing() -> None:
    solicitud = _solicitud(pauta_id=None)

    with pytest.raises(ValueError, match="pauta_id"):
        mark_as_published(solicitud)


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


def test_edit_solicitud_rejects_editing_a_published_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.PUBLICADA)

    with pytest.raises(ValueError, match="publicada"):
        edit_solicitud(solicitud, texto="Intento tardío")


def test_edit_solicitud_rejects_editing_a_cancelled_request() -> None:
    solicitud = _solicitud(estado=PublicationRequestStatus.CANCELADA, pauta_id=None)

    with pytest.raises(ValueError, match="cancelada"):
        edit_solicitud(solicitud, texto="Intento tardío")
