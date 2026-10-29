"""Unit tests for PillowPortadaRenderer — real rendering, no network, tiny synthetic photos."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from agents.images.pillow_portada_renderer import PillowPortadaRenderer
from core.ports.portada_renderer import PortadaError, SolicitudPortada, VariantePortada


def _foto(
    color: tuple[int, int, int] = (200, 120, 40), size: tuple[int, int] = (800, 600)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "JPEG")
    return buffer.getvalue()


def _abrir(datos: bytes) -> Image.Image:
    return Image.open(io.BytesIO(datos))


def test_renders_a_4_5_png_cover() -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(imagen_base=_foto(), titular="Titular de prueba")
    )

    imagen = _abrir(resultado)
    assert imagen.format == "PNG"
    assert imagen.size == (1080, 1350)


def test_renders_jpeg_when_asked() -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(imagen_base=_foto(), titular="Titular"), formato="jpeg"
    )

    assert _abrir(resultado).format == "JPEG"


def test_circle_template_changes_the_cover() -> None:
    renderer = PillowPortadaRenderer()
    sin = renderer.renderizar(SolicitudPortada(imagen_base=_foto(), titular="Titular"))
    con = renderer.renderizar(
        SolicitudPortada(
            imagen_base=_foto(), imagen_circulo=_foto((20, 200, 60)), titular="Titular"
        )
    )

    # The circle's centre sits inside the photo area; its pixel must come from the second photo.
    assert _abrir(con).convert("RGB").getpixel((814, 772)) != _abrir(sin).convert("RGB").getpixel(
        (814, 772)
    )


def test_variants_use_different_labels() -> None:
    renderer = PillowPortadaRenderer()
    noticias = renderer.renderizar(SolicitudPortada(imagen_base=_foto(), titular="T"))
    ultimo = renderer.renderizar(
        SolicitudPortada(imagen_base=_foto(), titular="T", variante=VariantePortada.LO_ULTIMO)
    )

    assert noticias != ultimo


def test_long_headline_and_emoji_do_not_break_the_render() -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(
            imagen_base=_foto(),
            antetitulo="🚨 ¡Última hora!",
            titular="Kbeto Zuleta será trasladado en avión ambulancia a Barranquilla e ingresará "
            "a UCI tras el accidente ocurrido en la vía entre El Difícil y Bosconia",
        )
    )

    assert _abrir(resultado).size == (1080, 1350)


def test_rejects_an_empty_headline() -> None:
    with pytest.raises(PortadaError):
        PillowPortadaRenderer().renderizar(SolicitudPortada(imagen_base=_foto(), titular="  🚨 "))


def test_rejects_an_unreadable_image() -> None:
    with pytest.raises(PortadaError):
        PillowPortadaRenderer().renderizar(
            SolicitudPortada(imagen_base=b"esto no es una imagen", titular="Titular")
        )
