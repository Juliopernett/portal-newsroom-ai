"""Unit test for the tz-aware branch of DestinoPublicacion's DB-to-domain mapping.

SQLite always drops tzinfo on round trip (see
`database/repositories/destino_publicacion_repository.py`), so no
SQLite-backed integration test ever exercises the branch where the stored
value already carries tzinfo — the branch a real PostgreSQL/Railway
database takes. Tested directly against the mapping function instead of a
live database, since that's a pure, DB-agnostic function.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.entities.destino_publicacion import CanalPublicacion, EstadoDestino
from database.models.destino_publicacion import DestinoPublicacionModel
from database.repositories.destino_publicacion_repository import _to_domain


def test_to_domain_keeps_an_already_timezone_aware_fecha_publicacion() -> None:
    fecha_publicacion = datetime(2026, 8, 6, 9, 0, tzinfo=UTC)
    model = DestinoPublicacionModel(
        id="destino-1",
        publication_request_id="solicitud-1",
        canal=CanalPublicacion.WORDPRESS.value,
        estado=EstadoDestino.PUBLICADO.value,
        wp_post_id="42",
        wp_url="https://example.com/?p=42",
        url_publicacion=None,
        registrado_por_user_id=None,
        fecha_publicacion=fecha_publicacion,
        ultimo_error=None,
    )

    destino = _to_domain(model)

    assert destino.fecha_publicacion == fecha_publicacion
    assert destino.fecha_publicacion is not None
    assert destino.fecha_publicacion.tzinfo is UTC


def test_to_domain_keeps_none_fecha_publicacion_for_a_pendiente_destino() -> None:
    model = DestinoPublicacionModel(
        id="destino-1",
        publication_request_id="solicitud-1",
        canal=CanalPublicacion.WORDPRESS.value,
        estado=EstadoDestino.PENDIENTE.value,
        wp_post_id=None,
        wp_url=None,
        url_publicacion=None,
        registrado_por_user_id=None,
        fecha_publicacion=None,
        ultimo_error=None,
    )

    destino = _to_domain(model)

    assert destino.fecha_publicacion is None
