"""Unit test for the tz-aware branch of MediaAsset's DB-to-domain mapping.

SQLite always drops tzinfo on round trip (see
`database/repositories/media_asset_repository.py`), so no SQLite-backed
integration test ever exercises the branch where the stored value
already carries tzinfo — the branch a real PostgreSQL/Railway database
takes. Tested directly against the mapping function instead of a live
database, since that's a pure, DB-agnostic function.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.entities.media_asset import MediaAssetType
from database.models.media_asset import MediaAssetModel
from database.repositories.media_asset_repository import _to_domain


def test_to_domain_keeps_an_already_timezone_aware_fecha_subida() -> None:
    fecha_subida = datetime(2026, 8, 6, 9, 0, tzinfo=UTC)
    model = MediaAssetModel(
        id="media-1",
        publication_request_id="solicitud-1",
        tipo=MediaAssetType.IMAGEN.value,
        nombre_archivo="foto.jpg",
        content_type="image/jpeg",
        tamano_bytes=1024,
        storage_key="solicitud-1/media-1",
        fecha_subida=fecha_subida,
        subido_por_user_id=None,
    )

    media = _to_domain(model)

    assert media.fecha_subida == fecha_subida
    assert media.fecha_subida.tzinfo is UTC


def test_to_domain_adds_utc_when_fecha_subida_is_naive() -> None:
    model = MediaAssetModel(
        id="media-1",
        publication_request_id="solicitud-1",
        tipo=MediaAssetType.VIDEO.value,
        nombre_archivo="clip.mp4",
        content_type="video/mp4",
        tamano_bytes=2048,
        storage_key="solicitud-1/media-1",
        fecha_subida=datetime(2026, 8, 6, 9, 0),
        subido_por_user_id="user-1",
    )

    media = _to_domain(model)

    assert media.fecha_subida.tzinfo is UTC
    assert media.tipo == MediaAssetType.VIDEO
    assert media.subido_por_user_id == "user-1"
