"""Unit tests for PillowPortadaRenderer — real rendering, no network, tiny synthetic photos."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from agents.images.pillow_portada_renderer import PillowPortadaRenderer, _unir_citas
from core.ports.portada_renderer import (
    MAX_CARACTERES_ANTETITULO,
    PortadaError,
    SolicitudPortada,
    VariantePortada,
)


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


@pytest.mark.parametrize(
    "antetitulo",
    [
        "¡Se unieron vallenato y carranga!",
        "¡Se unieron el vallenato, la carranga y la música popular en una sola canción!",
        "SUPERCALIFRAGILISTICOEXPIALIDOSOVALLENATODELMAGDALENAGRANDE",
    ],
)
def test_a_long_kicker_stays_inside_the_cover(antetitulo: str) -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(
            imagen_base=_foto((40, 40, 40)),
            antetitulo=antetitulo,
            titular="Heredero y Rafa Pérez estrenan Linda Remix, un tema que sabe a Colombia",
        )
    )

    imagen = _abrir(resultado).convert("RGB")
    # No white lettering may reach the side margins of the headline area.
    for x in (*range(0, 24), *range(1056, 1080)):
        for y in range(880, 1250):
            assert min(imagen.getpixel((x, y))) < 230, (x, y)


def _es_amarillo(pixel: tuple[int, ...]) -> bool:
    r, g, b = pixel[:3]
    return r > 205 and 190 < g < 225 and b < 70


def test_the_hook_button_stays_below_the_circle() -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(
            imagen_base=_foto((40, 40, 40)),
            imagen_circulo=_foto((40, 40, 40)),
            antetitulo="W" * MAX_CARACTERES_ANTETITULO,
            titular="Un titular muy largo que obliga a usar varias líneas debajo del gancho " * 2,
        )
    )

    imagen = _abrir(resultado).convert("RGB")
    filas = [
        y
        for y in range(700, 1270)
        if any(_es_amarillo(imagen.getpixel((x, y))) for x in range(1080))
    ]
    # The yellow button appears, all of it under the circle, which ends at y=967.
    assert filas and filas[0] > 975


def test_without_a_hook_nothing_is_yellow() -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(imagen_base=_foto((40, 40, 40)), titular="Titular sin gancho")
    )

    imagen = _abrir(resultado).convert("RGB")
    assert not any(
        _es_amarillo(imagen.getpixel((x, y)))
        for x in range(0, 1080, 2)
        for y in range(850, 1270, 2)
    )


def _foto_cuadrantes() -> bytes:
    """A 4:5 photo with a different colour in each quarter: nothing overflows."""
    imagen = Image.new("RGB", (800, 1000), (200, 0, 0))
    imagen.paste((0, 200, 0), (400, 0, 800, 500))
    imagen.paste((0, 0, 200), (0, 500, 400, 1000))
    imagen.paste((200, 200, 0), (400, 500, 800, 1000))
    buffer = io.BytesIO()
    imagen.save(buffer, "PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("enfoque_x", "enfoque_y", "esperado"),
    [(0.0, 0.0, (200, 0, 0)), (1.0, 0.0, (0, 200, 0)), (0.0, 1.0, (0, 0, 200))],
)
def test_zoom_lets_a_4_5_photo_move_both_ways(
    enfoque_x: float, enfoque_y: float, esperado: tuple[int, int, int]
) -> None:
    resultado = PillowPortadaRenderer().renderizar(
        SolicitudPortada(
            imagen_base=_foto_cuadrantes(),
            titular="T",
            enfoque_x=enfoque_x,
            enfoque_y=enfoque_y,
            zoom=2.0,
        )
    )

    # The centre of the photo area shows the quarter the focus points at.
    assert _abrir(resultado).convert("RGB").getpixel((540, 500)) == esperado


def test_every_category_has_its_own_label() -> None:
    renderer = PillowPortadaRenderer()
    portadas = {
        renderer.renderizar(SolicitudPortada(imagen_base=_foto(), titular="T", variante=v))
        for v in VariantePortada
    }

    assert len(portadas) == len(VariantePortada) == 5


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("ESTRENAN ‘LINDA REMIX’, YA", "ESTRENAN ‘LINDA\u00a0REMIX’, YA"),
        ('EL TEMA "MI GRAN AMOR" SUENA', 'EL TEMA "MI\u00a0GRAN\u00a0AMOR" SUENA'),
        ("‘UNA CITA DEMASIADO LARGA PARA UNA SOLA LÍNEA’", None),
    ],
)
def test_short_quoted_names_are_kept_together(texto: str, esperado: str | None) -> None:
    assert _unir_citas(texto) == (esperado or texto)


def test_rejects_an_empty_headline() -> None:
    with pytest.raises(PortadaError):
        PillowPortadaRenderer().renderizar(SolicitudPortada(imagen_base=_foto(), titular="  🚨 "))


def test_rejects_an_unreadable_image() -> None:
    with pytest.raises(PortadaError):
        PillowPortadaRenderer().renderizar(
            SolicitudPortada(imagen_base=b"esto no es una imagen", titular="Titular")
        )
