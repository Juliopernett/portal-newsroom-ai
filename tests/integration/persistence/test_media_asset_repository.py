"""Integration tests: SqlAlchemyMediaAssetRepository against a real SQLite schema."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.entities.media_asset import MediaAsset, MediaAssetType
from core.entities.publication_request import PublicationRequest
from database.repositories.media_asset_repository import SqlAlchemyMediaAssetRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)


def _create_solicitud(session: Session, **overrides: object) -> PublicationRequest:
    """Persist a PublicationRequest for a MediaAsset to reference as a real FK parent.

    `session.flush()` matters here for the same reason documented in
    `tests/integration/persistence/test_destino_publicacion_repository.py`:
    `media_assets` sorts alphabetically before `publication_requests`, so a
    single `session.commit()` covering both new rows would try to insert
    the child before the parent exists.
    """
    defaults: dict[str, object] = {"texto": "Solicitud de ejemplo"}
    defaults.update(overrides)
    solicitud = PublicationRequest(**defaults)
    SqlAlchemyPublicationRequestRepository(session).save(solicitud)
    session.flush()
    return solicitud


def _media(**overrides: object) -> MediaAsset:
    defaults: dict[str, object] = {
        "tipo": MediaAssetType.IMAGEN,
        "nombre_archivo": "foto.jpg",
        "content_type": "image/jpeg",
        "tamano_bytes": 1024,
        "storage_key": "solicitud-1/media-1",
    }
    defaults.update(overrides)
    return MediaAsset(**defaults)


def test_save_and_get_by_id_round_trips_a_media_asset(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    media = _media(publication_request_id=solicitud.id)

    repository.save(media)
    session.commit()

    assert repository.get_by_id(media.id) == media


def test_save_and_get_by_id_round_trips_a_video(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    media = _media(
        publication_request_id=solicitud.id,
        tipo=MediaAssetType.VIDEO,
        nombre_archivo="clip.mp4",
        content_type="video/mp4",
        tamano_bytes=5_000_000,
    )

    repository.save(media)
    session.commit()

    recuperado = repository.get_by_id(media.id)
    assert recuperado == media
    assert recuperado is not None
    assert recuperado.tipo == MediaAssetType.VIDEO


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyMediaAssetRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_list_by_publication_request_id_returns_only_its_own_media(session: Session) -> None:
    esta_solicitud = _create_solicitud(session)
    otra_solicitud = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    de_esta = _media(publication_request_id=esta_solicitud.id, storage_key="a/1")
    de_otra = _media(publication_request_id=otra_solicitud.id, storage_key="b/1")
    repository.save(de_esta)
    repository.save(de_otra)
    session.commit()

    resultado = repository.list_by_publication_request_id(esta_solicitud.id)

    assert [media.id for media in resultado] == [de_esta.id]


def test_list_by_publication_request_id_returns_multiple_media_for_one_solicitud(
    session: Session,
) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    foto = _media(publication_request_id=solicitud.id, storage_key="a/foto")
    video = _media(
        publication_request_id=solicitud.id,
        tipo=MediaAssetType.VIDEO,
        content_type="video/mp4",
        storage_key="a/video",
    )
    repository.save(foto)
    repository.save(video)
    session.commit()

    resultado = repository.list_by_publication_request_id(solicitud.id)

    assert {media.id for media in resultado} == {foto.id, video.id}


def test_list_all_returns_every_media_across_every_solicitud(session: Session) -> None:
    solicitud_a = _create_solicitud(session)
    solicitud_b = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    de_a = _media(publication_request_id=solicitud_a.id, storage_key="a/1")
    de_b = _media(publication_request_id=solicitud_b.id, storage_key="b/1")
    repository.save(de_a)
    repository.save(de_b)
    session.commit()

    resultado = repository.list_all()

    assert {media.id for media in resultado} == {de_a.id, de_b.id}


def test_delete_removes_the_media_asset(session: Session) -> None:
    solicitud = _create_solicitud(session)
    repository = SqlAlchemyMediaAssetRepository(session)
    media = _media(publication_request_id=solicitud.id)
    repository.save(media)
    session.commit()

    repository.delete(media.id)
    session.commit()

    assert repository.get_by_id(media.id) is None


def test_delete_is_a_noop_when_media_asset_does_not_exist(session: Session) -> None:
    repository = SqlAlchemyMediaAssetRepository(session)

    repository.delete("no-existe")  # no debe lanzar
