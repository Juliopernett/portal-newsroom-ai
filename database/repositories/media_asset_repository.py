"""SQLAlchemy adapter for `MediaAssetRepository`.

Translates between `core.entities.media_asset.MediaAsset` (domain) and
`database.models.media_asset.MediaAssetModel` (ORM). The domain never
sees this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.media_asset import MediaAsset, MediaAssetType
from database.models.media_asset import MediaAssetModel


def _to_model(media: MediaAsset) -> MediaAssetModel:
    return MediaAssetModel(
        id=media.id,
        publication_request_id=media.publication_request_id,
        tipo=media.tipo.value,
        nombre_archivo=media.nombre_archivo,
        content_type=media.content_type,
        tamano_bytes=media.tamano_bytes,
        storage_key=media.storage_key,
        fecha_subida=media.fecha_subida,
        subido_por_user_id=media.subido_por_user_id,
    )


def _to_domain(model: MediaAssetModel) -> MediaAsset:
    fecha_subida = model.fecha_subida
    if fecha_subida.tzinfo is None:
        # Same SQLite round-trip quirk handled in
        # database.repositories.publication_request_repository — see that
        # module's `_to_domain` for the full explanation.
        fecha_subida = fecha_subida.replace(tzinfo=UTC)
    return MediaAsset(
        id=model.id,
        publication_request_id=model.publication_request_id,
        tipo=MediaAssetType(model.tipo),
        nombre_archivo=model.nombre_archivo,
        content_type=model.content_type,
        tamano_bytes=model.tamano_bytes,
        storage_key=model.storage_key,
        fecha_subida=fecha_subida,
        subido_por_user_id=model.subido_por_user_id,
    )


class SqlAlchemyMediaAssetRepository:
    """`MediaAssetRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, media: MediaAsset) -> None:
        """Persist `media`, creating or updating it as needed."""
        self._session.merge(_to_model(media))

    def get_by_id(self, id: str) -> MediaAsset | None:
        """Return the `MediaAsset` identified by `id`, or `None`."""
        model = self._session.get(MediaAssetModel, id)
        return _to_domain(model) if model is not None else None

    def list_by_publication_request_id(self, publication_request_id: str) -> list[MediaAsset]:
        """Return every media asset attached to `publication_request_id`."""
        stmt = select(MediaAssetModel).where(
            MediaAssetModel.publication_request_id == publication_request_id
        )
        models = self._session.execute(stmt).scalars().all()
        return [_to_domain(model) for model in models]

    def list_all(self) -> list[MediaAsset]:
        """Return every media asset in the system — used by the purge script."""
        models = self._session.execute(select(MediaAssetModel)).scalars().all()
        return [_to_domain(model) for model in models]

    def delete(self, id: str) -> None:
        """Remove the `MediaAsset` row identified by `id` — a no-op if it does not exist."""
        model = self._session.get(MediaAssetModel, id)
        if model is not None:
            self._session.delete(model)
