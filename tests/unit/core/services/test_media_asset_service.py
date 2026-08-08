"""Unit tests for media_asset_service — pure, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.entities.media_asset import MediaAssetType
from core.entities.publication_request import PublicationRequest
from core.services.media_asset_service import (
    construir_storage_key,
    determinar_tipo,
    es_purgable,
    validar_tamano,
)

_AHORA = datetime(2026, 8, 20, tzinfo=UTC)


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {"texto": "Anuncio de prueba"}
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_es_purgable_false_when_solicitud_still_open() -> None:
    solicitud = _solicitud(fecha_cierre=None)

    assert es_purgable(solicitud, retencion_dias=7, ahora=_AHORA) is False


def test_es_purgable_false_before_retencion_dias_elapse() -> None:
    solicitud = _solicitud(fecha_cierre=_AHORA - timedelta(days=3))

    assert es_purgable(solicitud, retencion_dias=7, ahora=_AHORA) is False


def test_es_purgable_true_exactly_at_retencion_boundary() -> None:
    solicitud = _solicitud(fecha_cierre=_AHORA - timedelta(days=7))

    assert es_purgable(solicitud, retencion_dias=7, ahora=_AHORA) is True


def test_es_purgable_true_well_past_retencion_dias() -> None:
    solicitud = _solicitud(fecha_cierre=_AHORA - timedelta(days=30))

    assert es_purgable(solicitud, retencion_dias=7, ahora=_AHORA) is True


@pytest.mark.parametrize(
    ("content_type", "esperado"),
    [
        ("image/jpeg", MediaAssetType.IMAGEN),
        ("image/png", MediaAssetType.IMAGEN),
        ("video/mp4", MediaAssetType.VIDEO),
        ("video/quicktime", MediaAssetType.VIDEO),
    ],
)
def test_determinar_tipo_accepts_image_and_video(
    content_type: str, esperado: MediaAssetType
) -> None:
    assert determinar_tipo(content_type) is esperado


@pytest.mark.parametrize("content_type", ["audio/mpeg", "application/pdf", "text/plain", ""])
def test_determinar_tipo_rejects_anything_else(content_type: str) -> None:
    with pytest.raises(ValueError, match="no soportado"):
        determinar_tipo(content_type)


def test_validar_tamano_accepts_within_limit() -> None:
    validar_tamano(
        MediaAssetType.IMAGEN, 1000, max_bytes_imagen=2000, max_bytes_video=1_000_000
    )  # no debe lanzar


def test_validar_tamano_accepts_exactly_at_limit() -> None:
    validar_tamano(
        MediaAssetType.IMAGEN, 2000, max_bytes_imagen=2000, max_bytes_video=1_000_000
    )  # no debe lanzar


def test_validar_tamano_rejects_imagen_over_its_own_limit() -> None:
    with pytest.raises(ValueError, match="máximo"):
        validar_tamano(
            MediaAssetType.IMAGEN, 2001, max_bytes_imagen=2000, max_bytes_video=1_000_000
        )


def test_validar_tamano_rejects_video_over_its_own_limit_not_imagen_limit() -> None:
    with pytest.raises(ValueError, match="máximo"):
        validar_tamano(MediaAssetType.VIDEO, 3000, max_bytes_imagen=2000, max_bytes_video=2500)


def test_construir_storage_key_combines_solicitud_and_media_ids() -> None:
    assert construir_storage_key("solicitud-1", "media-1") == "solicitud-1/media-1"
