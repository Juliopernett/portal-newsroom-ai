"""Unit tests for the MediaAsset entity."""

from __future__ import annotations

import pytest

from core.entities.media_asset import MediaAsset, MediaAssetType


def _build(**overrides: object) -> MediaAsset:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "tipo": MediaAssetType.IMAGEN,
        "nombre_archivo": "portada.jpg",
        "content_type": "image/jpeg",
        "tamano_bytes": 1024,
        "storage_key": "solicitud-1/portada.jpg",
    }
    defaults.update(overrides)
    return MediaAsset(**defaults)


def test_create_media_asset_assigns_defaults() -> None:
    media = _build()

    assert media.id
    assert media.publication_request_id == "solicitud-1"
    assert media.tipo == MediaAssetType.IMAGEN
    assert media.nombre_archivo == "portada.jpg"
    assert media.content_type == "image/jpeg"
    assert media.tamano_bytes == 1024
    assert media.storage_key == "solicitud-1/portada.jpg"
    assert media.fecha_subida is not None
    assert media.subido_por_user_id is None


def test_create_media_asset_rejects_empty_publication_request_id() -> None:
    with pytest.raises(ValueError, match="publication_request_id"):
        _build(publication_request_id="")


def test_create_media_asset_rejects_empty_nombre_archivo() -> None:
    with pytest.raises(ValueError, match="nombre_archivo"):
        _build(nombre_archivo="")


def test_create_media_asset_rejects_empty_content_type() -> None:
    with pytest.raises(ValueError, match="content_type"):
        _build(content_type="")


def test_create_media_asset_rejects_empty_storage_key() -> None:
    with pytest.raises(ValueError, match="storage_key"):
        _build(storage_key="")


@pytest.mark.parametrize("tamano", [0, -1])
def test_create_media_asset_rejects_non_positive_tamano_bytes(tamano: int) -> None:
    with pytest.raises(ValueError, match="tamano_bytes"):
        _build(tamano_bytes=tamano)


def test_video_type_accepted() -> None:
    media = _build(tipo=MediaAssetType.VIDEO, content_type="video/mp4")

    assert media.tipo == MediaAssetType.VIDEO


def test_media_asset_is_immutable() -> None:
    media = _build()

    with pytest.raises(AttributeError):
        media.nombre_archivo = "otro.jpg"  # type: ignore[misc]
