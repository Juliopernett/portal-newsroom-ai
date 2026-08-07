"""Integration tests: SqlAlchemyDestinoPublicacionRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.publication_request import PublicationRequest
from database.repositories.destino_publicacion_repository import (
    SqlAlchemyDestinoPublicacionRepository,
)
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)


def _create_solicitud(session: Session, **overrides: object) -> PublicationRequest:
    """Persist a PublicationRequest for a destino to reference as a real FK parent.

    `session.flush()` (not just `save()`) matters here: `destinos_publicacion`
    sorts alphabetically before `publication_requests`, so a single
    `session.commit()` covering both new rows would try to insert the
    child before the parent exists — the same ordering pitfall already
    documented for `sessions`/`users` (see database/unit_of_work.py's
    history). Flushing the parent immediately sidesteps it.
    """
    defaults: dict[str, object] = {"texto": "Solicitud de ejemplo"}
    defaults.update(overrides)
    solicitud = PublicationRequest(**defaults)
    SqlAlchemyPublicationRequestRepository(session).save(solicitud)
    session.flush()
    return solicitud


def _destino(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {"canal": CanalPublicacion.WORDPRESS}
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_save_and_get_by_id_round_trips_a_pendiente_destino(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    destino = _destino(publication_request_id=solicitud.id)

    repository.save(destino)
    session.commit()

    assert repository.get_by_id(destino.id) == destino


def test_save_and_get_by_id_round_trips_a_publicado_wordpress_destino(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    destino = _destino(
        publication_request_id=solicitud.id,
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        wp_post_id="42",
        wp_url="https://portalvallenato.com/?p=42",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    repository.save(destino)
    session.commit()

    recuperado = repository.get_by_id(destino.id)
    assert recuperado == destino
    assert recuperado is not None
    assert recuperado.wp_post_id == "42"


def test_save_and_get_by_id_round_trips_a_publicado_facebook_destino(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    destino = _destino(
        publication_request_id=solicitud.id,
        canal=CanalPublicacion.FACEBOOK,
        estado=EstadoDestino.PUBLICADO,
        url_publicacion="https://facebook.com/post/1",
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    repository.save(destino)
    session.commit()

    assert repository.get_by_id(destino.id) == destino


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyDestinoPublicacionRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_list_by_publication_request_id_returns_only_its_own_destinos(session: Session) -> None:
    esta_solicitud = _create_solicitud(session)
    otra_solicitud = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    de_esta = _destino(publication_request_id=esta_solicitud.id, canal=CanalPublicacion.WORDPRESS)
    de_otra = _destino(publication_request_id=otra_solicitud.id, canal=CanalPublicacion.WORDPRESS)
    repository.save(de_esta)
    repository.save(de_otra)
    session.commit()

    resultado = repository.list_by_publication_request_id(esta_solicitud.id)

    assert [destino.id for destino in resultado] == [de_esta.id]


def test_list_by_publication_request_id_returns_multiple_destinos_for_one_solicitud(
    session: Session,
) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    wordpress = _destino(publication_request_id=solicitud.id, canal=CanalPublicacion.WORDPRESS)
    instagram = _destino(publication_request_id=solicitud.id, canal=CanalPublicacion.INSTAGRAM)
    repository.save(wordpress)
    repository.save(instagram)
    session.commit()

    resultado = repository.list_by_publication_request_id(solicitud.id)

    assert {destino.id for destino in resultado} == {wordpress.id, instagram.id}


def test_list_all_returns_every_destino_across_every_solicitud(session: Session) -> None:
    solicitud_a = _create_solicitud(session)
    solicitud_b = _create_solicitud(session)
    repository = SqlAlchemyDestinoPublicacionRepository(session)
    de_a = _destino(publication_request_id=solicitud_a.id, canal=CanalPublicacion.WORDPRESS)
    de_b = _destino(publication_request_id=solicitud_b.id, canal=CanalPublicacion.INSTAGRAM)
    repository.save(de_a)
    repository.save(de_b)
    session.commit()

    resultado = repository.list_all()

    assert {destino.id for destino in resultado} == {de_a.id, de_b.id}
