"""Unit test for scripts.purgar_media_expirados._media_purgable — pure, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.entities.media_asset import MediaAsset, MediaAssetType
from core.entities.publication_request import PublicationRequest
from scripts.purgar_media_expirados import _media_purgable

_AHORA = datetime(2026, 8, 20, tzinfo=UTC)


def _media(**overrides: object) -> MediaAsset:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "tipo": MediaAssetType.IMAGEN,
        "nombre_archivo": "foto.jpg",
        "content_type": "image/jpeg",
        "tamano_bytes": 100,
        "storage_key": "solicitud-1/foto.jpg",
    }
    defaults.update(overrides)
    return MediaAsset(**defaults)


def test_media_purgable_skips_a_media_asset_whose_solicitud_is_unknown() -> None:
    media = _media(publication_request_id="huerfana")

    resultado = _media_purgable({}, [media], retencion_dias=7, ahora=_AHORA)

    assert resultado == []


def test_media_purgable_includes_media_of_a_purgable_solicitud() -> None:
    solicitud = PublicationRequest(
        id="solicitud-1", texto="Anuncio", fecha_cierre=_AHORA - timedelta(days=30)
    )
    media = _media(publication_request_id="solicitud-1")

    resultado = _media_purgable({"solicitud-1": solicitud}, [media], retencion_dias=7, ahora=_AHORA)

    assert resultado == [media]
