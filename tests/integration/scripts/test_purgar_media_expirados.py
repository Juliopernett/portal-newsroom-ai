"""Integration tests: scripts/purgar_media_expirados.py.

`purgar()` is called with explicit `session_factory`/`storage`/
`retencion_dias`/`ahora` — never the real `.env`-backed defaults, same
isolation discipline as every other test in this suite.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from agents.storage.local_disk import LocalDiskMediaStorage
from core.entities.media_asset import MediaAsset, MediaAssetType
from core.entities.publication_request import PublicationRequest
from database.repositories.media_asset_repository import SqlAlchemyMediaAssetRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)
from database.unit_of_work import SqlAlchemyUnitOfWork
from scripts.purgar_media_expirados import purgar

_AHORA = datetime(2026, 8, 20, tzinfo=UTC)
_RETENCION_DIAS = 7


def _seed(
    session_factory: sessionmaker[Session],
    storage: LocalDiskMediaStorage,
    *,
    fecha_cierre: datetime | None,
    contenido: bytes = b"contenido",
) -> tuple[PublicationRequest, MediaAsset]:
    session = session_factory()
    solicitud = PublicationRequest(texto="Anuncio", fecha_cierre=fecha_cierre)
    SqlAlchemyPublicationRequestRepository(session).save(solicitud)
    session.flush()
    media = MediaAsset(
        publication_request_id=solicitud.id,
        tipo=MediaAssetType.IMAGEN,
        nombre_archivo="foto.jpg",
        content_type="image/jpeg",
        tamano_bytes=len(contenido),
        storage_key=f"{solicitud.id}/foto.jpg",
    )
    SqlAlchemyMediaAssetRepository(session).save(media)
    storage.guardar(media.storage_key, contenido)
    session.commit()
    session.close()
    return solicitud, media


def test_purgar_does_nothing_when_no_media_exists(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )  # no debe lanzar


def test_purgar_keeps_media_of_a_still_open_solicitud(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _solicitud, media = _seed(session_factory, storage, fecha_cierre=None)

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media.id) is not None
    assert storage.leer(media.storage_key) == b"contenido"


def test_purgar_keeps_media_before_retencion_dias_elapse(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _solicitud, media = _seed(session_factory, storage, fecha_cierre=_AHORA - timedelta(days=3))

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media.id) is not None


def test_purgar_deletes_file_and_row_past_retencion_dias(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _solicitud, media = _seed(session_factory, storage, fecha_cierre=_AHORA - timedelta(days=30))

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media.id) is None
    assert not (tmp_path / "media" / media.storage_key).exists()


def test_purgar_dry_run_reports_but_does_not_delete(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _solicitud, media = _seed(session_factory, storage, fecha_cierre=_AHORA - timedelta(days=30))

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
        dry_run=True,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media.id) is not None
    assert storage.leer(media.storage_key) == b"contenido"


def test_purgar_is_idempotent_when_run_twice(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _solicitud, media = _seed(session_factory, storage, fecha_cierre=_AHORA - timedelta(days=30))

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )
    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )  # segunda corrida no debe lanzar

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media.id) is None


def test_purgar_only_removes_solicitudes_past_retention_leaves_others(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    _s_vieja, media_vieja = _seed(
        session_factory, storage, fecha_cierre=_AHORA - timedelta(days=30), contenido=b"vieja"
    )
    _s_nueva, media_nueva = _seed(
        session_factory, storage, fecha_cierre=_AHORA - timedelta(days=1), contenido=b"nueva"
    )

    purgar(
        session_factory=session_factory,
        storage=storage,
        retencion_dias=_RETENCION_DIAS,
        ahora=_AHORA,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.media_assets.get_by_id(media_vieja.id) is None
        assert uow.media_assets.get_by_id(media_nueva.id) is not None
