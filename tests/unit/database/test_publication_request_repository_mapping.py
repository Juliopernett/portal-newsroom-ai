"""Unit test for the tz-aware branch of PublicationRequest's DB-to-domain mapping.

SQLite always drops tzinfo on round trip (see
`database/repositories/publication_request_repository.py`), so no
SQLite-backed integration test ever exercises the branch where the stored
value already carries tzinfo — the branch a real PostgreSQL/Railway
database takes. Tested directly against the mapping function instead of a
live database, since that's a pure, DB-agnostic function.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.entities.publication_request import PublicationRequestStatus
from database.models.publication_request import PublicationRequestModel
from database.repositories.publication_request_repository import _to_domain


def test_to_domain_keeps_an_already_timezone_aware_fecha_recepcion() -> None:
    fecha_recepcion = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
    model = PublicationRequestModel(
        id="solicitud-1",
        pauta_id="pauta-1",
        fecha_recepcion=fecha_recepcion,
        texto="Solicitud de ejemplo",
        estado=PublicationRequestStatus.RECIBIDA.value,
        prioridad_manual=False,
        observaciones=None,
    )

    solicitud = _to_domain(model)

    assert solicitud.fecha_recepcion == fecha_recepcion
    assert solicitud.fecha_recepcion.tzinfo is UTC
