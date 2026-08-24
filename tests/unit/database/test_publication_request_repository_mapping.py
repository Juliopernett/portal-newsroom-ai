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

from core.entities.publication_request import EstadoPreparacionIA, PublicationRequestStatus
from database.models.publication_request import PublicationRequestModel
from database.repositories.publication_request_repository import _to_domain


def _model(**overrides: object) -> PublicationRequestModel:
    defaults: dict[str, object] = {
        "id": "solicitud-1",
        "pauta_id": "pauta-1",
        "fecha_recepcion": datetime(2026, 7, 30, 9, 0, tzinfo=UTC),
        "texto": "Solicitud de ejemplo",
        "estado": PublicationRequestStatus.RECIBIDA.value,
        "prioridad_manual": False,
        "observaciones": None,
        # `preparacion_ia_estado`'s NOT NULL default only applies on a real
        # INSERT (SQLAlchemy mapper defaults, not Python attribute
        # defaults) — a model built in memory like this must set it
        # explicitly, the same as a row inserted before this migration
        # would read back as (see the migration's server_default).
        "preparacion_ia_estado": EstadoPreparacionIA.PENDIENTE.value,
    }
    defaults.update(overrides)
    return PublicationRequestModel(**defaults)


def test_to_domain_keeps_an_already_timezone_aware_fecha_recepcion() -> None:
    fecha_recepcion = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
    model = _model(fecha_recepcion=fecha_recepcion)

    solicitud = _to_domain(model)

    assert solicitud.fecha_recepcion == fecha_recepcion
    assert solicitud.fecha_recepcion.tzinfo is UTC


def test_to_domain_maps_editorial_fields_when_present() -> None:
    model = _model(
        contenido_editorial="Cuerpo reescrito",
        entradilla_editorial="Entradilla",
        titulo_editorial="Titular IA",
        categoria_editorial="Noticias",
        etiquetas_editorial='["vallenato", "lanzamiento"]',
        slug_editorial="titular-ia",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO.value,
        preparacion_ia_error=None,
    )

    solicitud = _to_domain(model)

    assert solicitud.contenido_editorial == "Cuerpo reescrito"
    assert solicitud.entradilla_editorial == "Entradilla"
    assert solicitud.titulo_editorial == "Titular IA"
    assert solicitud.categoria_editorial == "Noticias"
    assert solicitud.etiquetas_editorial == ("vallenato", "lanzamiento")
    assert solicitud.slug_editorial == "titular-ia"
    assert solicitud.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO


def test_to_domain_leaves_editorial_fields_none_when_never_prepared() -> None:
    solicitud = _to_domain(_model())

    assert solicitud.contenido_editorial is None
    assert solicitud.etiquetas_editorial is None
    assert solicitud.preparacion_ia_estado == EstadoPreparacionIA.PENDIENTE
    assert solicitud.preparacion_ia_error is None
