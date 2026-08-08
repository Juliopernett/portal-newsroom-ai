"""Purge MediaAsset attachments whose PublicationRequest is long complete.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md, Decision
3). A deliberate ops-triggered script, not a scheduler running inside
the FastAPI process — same reasoning as `scripts/create_user.py` and
`scripts/migrate_historical_data.py`: fewer moving parts in a system
already carrying real production traffic. Run it by hand, or schedule it
via Railway's cron support — the script itself doesn't change either
way.

Idempotent: a `MediaAsset` whose underlying file is already gone (e.g.
purged by a previous run that crashed after deleting the file but before
committing its DB row) is still removed cleanly —
`MediaStorage.eliminar` is a documented no-op when the key doesn't
exist.

Usage:
    python -m scripts.purgar_media_expirados            # purga real
    python -m scripts.purgar_media_expirados --dry-run   # solo reporta
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from agents.storage.local_disk import LocalDiskMediaStorage
from config.settings import get_settings
from core.entities.media_asset import MediaAsset
from core.entities.publication_request import PublicationRequest
from core.ports.media_storage import MediaStorage
from core.services.media_asset_service import es_purgable
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from shared.logger import get_logger

logger = get_logger(__name__)


def _media_purgable(
    solicitudes_por_id: dict[str, PublicationRequest],
    media_assets: list[MediaAsset],
    *,
    retencion_dias: int,
    ahora: datetime,
) -> list[MediaAsset]:
    """Return the subset of `media_assets` whose parent solicitud is purgable.

    A media asset whose `publication_request_id` no longer resolves to a
    real solicitud (should not happen — the FK forbids it — but this
    keeps the function total) is skipped rather than treated as purgable.
    """
    resultado = []
    for media in media_assets:
        solicitud = solicitudes_por_id.get(media.publication_request_id)
        if solicitud is None:
            continue
        if es_purgable(solicitud, retencion_dias=retencion_dias, ahora=ahora):
            resultado.append(media)
    return resultado


def purgar(
    *,
    session_factory: sessionmaker[Session] | None = None,
    storage: MediaStorage | None = None,
    retencion_dias: int | None = None,
    ahora: datetime | None = None,
    dry_run: bool = False,
) -> None:
    """Delete every MediaAsset (file + row) whose solicitud is past retention.

    Every keyword defaults to the real, `.env`-backed value (`Settings`,
    `get_session_factory()`, a `LocalDiskMediaStorage` over
    `media_storage_dir`) — `main()` calls this with no overrides. Tests
    pass explicit values instead, the same isolation discipline
    `app.api.dependencies.get_unit_of_work` gets overridden for in API
    tests, so a test run never touches the real database or disk.
    """
    settings = get_settings()
    session_factory = session_factory or get_session_factory()
    storage = storage or LocalDiskMediaStorage(settings.media_storage_dir)
    retencion_dias = settings.media_retention_dias if retencion_dias is None else retencion_dias
    ahora = ahora or datetime.now(UTC)

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        solicitudes_por_id = {s.id: s for s in uow.publication_requests.list_all()}
        purgables = _media_purgable(
            solicitudes_por_id,
            uow.media_assets.list_all(),
            retencion_dias=retencion_dias,
            ahora=ahora,
        )

        if not purgables:
            logger.info("Nada que purgar (retención: %s días).", retencion_dias)
            return

        bytes_liberados = 0
        for media in purgables:
            logger.info(
                "%s: %s (%s bytes, solicitud %s)",
                "Purgaría" if dry_run else "Purgando",
                media.nombre_archivo,
                media.tamano_bytes,
                media.publication_request_id,
            )
            if not dry_run:
                storage.eliminar(media.storage_key)
                uow.media_assets.delete(media.id)
            bytes_liberados += media.tamano_bytes

        if dry_run:
            logger.info(
                "Dry-run: %s archivo(s), %s bytes se purgarían.", len(purgables), bytes_liberados
            )
            return

        uow.commit()
        logger.info("Purgados %s archivo(s), %s bytes liberados.", len(purgables), bytes_liberados)


def main() -> None:
    """Parse arguments and run the purge."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reporta qué se purgaría sin borrar nada.",
    )
    args = parser.parse_args()
    purgar(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
