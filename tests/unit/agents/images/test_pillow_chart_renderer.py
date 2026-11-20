"""Unit tests for the weekly Chart cards — real rendering, no network, synthetic pictures."""

from __future__ import annotations

import io
from datetime import date

import pytest
from PIL import Image

from agents.images.descarga_imagenes import _permitida, descargar_imagenes
from agents.images.pillow_chart_renderer import (
    ChartImagenError,
    FilaImagen,
    PillowChartRenderer,
    _rango_semana,
    _vistas,
)


def _foto(color: tuple[int, int, int] = (200, 120, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (480, 360), color).save(buffer, "JPEG")
    return buffer.getvalue()


def _filas(n: int = 10, con_fotos: bool = True) -> list[FilaImagen]:
    return [
        FilaImagen(
            posicion=i,
            titulo=f"Canción número {i} con un título bastante largo para forzar el recorte",
            artista=f"Artista {i}" if i != 4 else None,
            vistas_semana=3_000_000 // i,
            tendencia=("sube", "baja", "igual", "nuevo", None)[i % 5],
            foto_artista=_foto() if con_fotos else None,
            miniatura=_foto((20, 90, 160)) if con_fotos and i == 1 else None,
        )
        for i in range(1, n + 1)
    ]


@pytest.mark.parametrize(
    ("formato", "alto"),
    [("feed", 1350), ("historia", 1920)],
)
@pytest.mark.parametrize("lamina", ["portada", "lista"])
def test_renders_every_card_at_its_social_size(lamina: str, formato: str, alto: int) -> None:
    png = PillowChartRenderer().renderizar(
        date(2026, 11, 20),
        _filas(),
        lamina=lamina,
        formato=formato,  # type: ignore[arg-type]
    )
    imagen = Image.open(io.BytesIO(png))
    assert imagen.format == "PNG"
    assert imagen.size == (1080, alto)


def test_renders_without_any_picture_using_initials() -> None:
    png = PillowChartRenderer().renderizar(
        date(2026, 11, 20), _filas(con_fotos=False), lamina="portada"
    )
    assert Image.open(io.BytesIO(png)).size == (1080, 1350)


def test_renders_with_fewer_than_ten_rows() -> None:
    for n in (1, 2, 3):
        for lamina in ("portada", "lista"):
            PillowChartRenderer().renderizar(
                date(2026, 11, 20),
                _filas(n),
                lamina=lamina,  # type: ignore[arg-type]
            )


def test_unreadable_pictures_fall_back_instead_of_failing() -> None:
    filas = [FilaImagen(1, "Tema", "Artista", 1000, None, b"no es una imagen", b"tampoco")]
    PillowChartRenderer().renderizar(date(2026, 11, 20), filas, lamina="portada")


def test_empty_edition_is_an_error() -> None:
    with pytest.raises(ChartImagenError):
        PillowChartRenderer().renderizar(date(2026, 11, 20), [], lamina="lista")


def test_week_range_wording() -> None:
    assert _rango_semana(date(2026, 11, 20)) == "14 al 20 de noviembre"
    assert _rango_semana(date(2026, 12, 4)) == "28 de noviembre al 4 de diciembre"


def test_view_counts_read_like_a_headline() -> None:
    assert _vistas(2_400_000) == "2,4 M"
    assert _vistas(845_200) == "845 mil"
    assert _vistas(4_300) == "4,3 mil"
    assert _vistas(120) == "120"


def test_only_the_website_and_youtube_thumbnails_are_downloadable() -> None:
    assert _permitida("https://portalvallenato.com/wp-content/uploads/a.webp")
    assert _permitida("https://i.ytimg.com/vi/abc/hqdefault.jpg")
    assert not _permitida("http://portalvallenato.com/a.jpg")  # not https
    assert not _permitida("https://evil.example.com/a.jpg")
    assert not _permitida("https://portalvallenato.com.evil.example/a.jpg")
    assert not _permitida("https://169.254.169.254/latest/meta-data")
    assert descargar_imagenes(["https://evil.example.com/a.jpg", ""]) == {}


def test_watermark_changes_the_card_so_a_preview_is_never_the_real_one() -> None:
    renderer = PillowChartRenderer()
    sin = renderer.renderizar(date(2026, 11, 20), _filas(), lamina="lista")
    con = renderer.renderizar(
        date(2026, 11, 20), _filas(), lamina="lista", marca_agua="VISTA PREVIA EN VIVO"
    )
    assert sin != con
    assert Image.open(io.BytesIO(con)).size == (1080, 1350)


def test_a_missing_artist_photo_falls_back_to_the_video_thumbnail_not_initials() -> None:
    def fila(miniatura: bytes | None) -> list[FilaImagen]:
        return [FilaImagen(1, "Tema", "Artista Nuevo", 1000, None, None, miniatura)]

    renderer = PillowChartRenderer()
    con_miniatura = renderer.renderizar(
        date(2026, 11, 20), fila(_foto((20, 90, 160))), lamina="lista"
    )
    solo_iniciales = renderer.renderizar(date(2026, 11, 20), fila(None), lamina="lista")
    assert con_miniatura != solo_iniciales
