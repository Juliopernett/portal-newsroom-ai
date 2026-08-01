"""Unit tests for mark_as_published and link_pauta."""

from __future__ import annotations

import pytest

from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.publication_request_service import link_pauta, mark_as_published


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
