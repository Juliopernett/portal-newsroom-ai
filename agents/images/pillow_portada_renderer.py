"""Pillow adapter for `core.ports.portada_renderer.PortadaRenderer`.

Reproduces the team's Canva "Formato 4:5 portal vallenato" templates
(1080x1350). Every coordinate below was read from the Canva design itself
(2026-10-29), not eyeballed: label box, hashtag, logo, gradient, headline
box, footer and the highlight circle keep the template's positions.

Fonts are open source (SIL OFL, `assets/OFL-licencia-fuentes.txt`): Anton
stands in for the template's condensed headline font, Montserrat for the
label/hashtag/footer. They are bundled in `assets/` so the render never
depends on fonts installed on the server.
"""

from __future__ import annotations

import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from core.ports.portada_renderer import PortadaError, SolicitudPortada, VariantePortada

_ASSETS = Path(__file__).parent / "assets"

_ANCHO, _ALTO = 1080, 1350
_AZUL = (0x3B, 0x58, 0x98)
_BLANCO = (255, 255, 255)
_NEGRO = (0, 0, 0)

# Gradient: Canva stacks ~5 copies of a transparent->blue image spanning
# y=852..1638 (only the top of it falls inside the canvas).
_GRAD_INICIO, _GRAD_LARGO, _GRAD_CAPAS = 852, 786, 5.3

# Headline box (template page 1/4): centered, bottom-anchored.
_TITULAR_ANCHO = 1008
_TITULAR_BASE_Y = 1243
_TITULAR_ALTO_MAX = 235
_TITULAR_TAMANO_MAX = 103
_TITULAR_TAMANO_MIN = 52
_TITULAR_INTERLINEA = 1.07
_TITULAR_TRACKING = 0.01
# Anton is wider than the template's font; with this scale and tracking the
# template's own sample line ("‘VAMOS PA’ AFUERA CON NUEVA") measures ~950px, as in Canva.
_TITULAR_ESCALA = 0.90
_SOMBRA = (-6, 6)
_ANTETITULO_FACTOR = 1.38

# Highlight circle (template page 3/4).
_CIRCULO_CENTRO = (814, 772)
_CIRCULO_DIAMETRO = 391
_CIRCULO_BORDE = 8
_CIRCULO_COLOR_BORDE = (0xF9, 0xEB, 0xE9)

_ETIQUETAS = {VariantePortada.NOTICIAS: "NOTICIAS", VariantePortada.LO_ULTIMO: "LO ÚLTIMO"}

# Emoji have no glyph in the bundled fonts; drop them instead of printing tofu boxes.
_EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿️‍]")


def _fuente(archivo: str, tamano: float, peso: int | None = None) -> ImageFont.FreeTypeFont:
    fuente = ImageFont.truetype(str(_ASSETS / archivo), size=round(tamano))
    if peso is not None:
        fuente.set_variation_by_axes([peso])
    return fuente


def _ancho(texto: str, fuente: ImageFont.FreeTypeFont, tracking: float) -> float:
    return fuente.getlength(texto) + tracking * max(len(texto) - 1, 0)


def _dibujar(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    texto: str,
    fuente: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    tracking: float,
) -> None:
    """Draw `texto` with its left edge at `x` and baseline at `y`, with letter-spacing.

    Each glyph is placed at the prefix's real advance (so kerning pairs
    survive) plus the cumulative tracking.
    """
    for i, caracter in enumerate(texto):
        if caracter == " ":
            continue
        cx = x + fuente.getlength(texto[:i]) + tracking * i
        draw.text((cx, y), caracter, font=fuente, fill=color, anchor="ls")


def _cubrir(imagen: Image.Image, ancho: int, alto: int, fx: float, fy: float) -> Image.Image:
    """Scale-and-crop `imagen` to fill `ancho`x`alto`, keeping the (fx, fy) focus."""
    return ImageOps.fit(imagen, (ancho, alto), Image.LANCZOS, centering=(fx, fy))


def _abrir(datos: bytes, nombre: str) -> Image.Image:
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen = ImageOps.exif_transpose(imagen)
        return imagen.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PortadaError(f"No se pudo leer la {nombre}: {exc}") from exc


def _degradado() -> Image.Image:
    capa = Image.new("RGBA", (_ANCHO, _ALTO), (*_AZUL, 0))
    px = capa.load()
    for y in range(_ALTO):
        t = min(max((y - _GRAD_INICIO) / _GRAD_LARGO, 0.0), 1.0)
        alfa = int(255 * (1 - (1 - t) ** _GRAD_CAPAS))
        if alfa:
            for x in range(_ANCHO):
                px[x, y] = (*_AZUL, alfa)
    return capa


def _envolver(
    texto: str, fuente: ImageFont.FreeTypeFont, tracking: float, ancho_max: float
) -> list[str]:
    lineas: list[str] = []
    actual = ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and _ancho(prueba, fuente, tracking) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def _limpiar(texto: str) -> str:
    return " ".join(_EMOJI.sub("", texto).split()).upper()


class PillowPortadaRenderer:
    """`PortadaRenderer` implemented with Pillow."""

    def renderizar(self, solicitud: SolicitudPortada, *, formato: str = "png") -> bytes:
        titular = _limpiar(solicitud.titular)
        antetitulo = _limpiar(solicitud.antetitulo) if solicitud.antetitulo else ""
        if not titular:
            raise PortadaError("El titular no puede estar vacío")

        base = _abrir(solicitud.imagen_base, "imagen base")
        lienzo = _cubrir(base, _ANCHO, _ALTO, solicitud.enfoque_x, solicitud.enfoque_y)
        lienzo = lienzo.convert("RGBA")
        lienzo.alpha_composite(_degradado())

        if solicitud.imagen_circulo is not None:
            self._circulo(lienzo, _abrir(solicitud.imagen_circulo, "imagen del círculo"))

        draw = ImageDraw.Draw(lienzo)
        self._cabecera(lienzo, draw, solicitud.variante)
        self._titular(draw, antetitulo, titular)
        self._pie(lienzo, draw)

        salida = io.BytesIO()
        if formato.lower() in ("jpg", "jpeg"):
            lienzo.convert("RGB").save(salida, "JPEG", quality=92, optimize=True)
        else:
            lienzo.convert("RGB").save(salida, "PNG", optimize=True)
        return salida.getvalue()

    # --- partes de la plantilla -------------------------------------------

    def _cabecera(
        self, lienzo: Image.Image, draw: ImageDraw.ImageDraw, variante: VariantePortada
    ) -> None:
        # Etiqueta: caja negra que sale del borde izquierdo, texto en cursiva negrita.
        fuente = _fuente("Montserrat-Italic.ttf", 33, 700)
        etiqueta = _ETIQUETAS[variante]
        ancho_texto = _ancho(etiqueta, fuente, 0.17)
        draw.rectangle((0, 7.4, 14 + ancho_texto + 26, 81.8), fill=_NEGRO)
        _dibujar(draw, 14, 56.5, etiqueta, fuente, _BLANCO, 0.17)

        # #NoticiasVallenatas alineado a la derecha, antes del logo.
        fuente = _fuente("Montserrat.ttf", 36, 300)
        hashtag = "#NoticiasVallenatas"
        tracking = -1.5
        _dibujar(
            draw, 930.4 - _ancho(hashtag, fuente, tracking), 58, hashtag, fuente, _BLANCO, tracking
        )

        # Logo circular de 186px que se sale por la esquina superior derecha.
        logo = Image.open(_ASSETS / "logo-pv-original.png").convert("RGBA")
        logo = logo.resize((186, 186), Image.LANCZOS).rotate(1, resample=Image.BICUBIC)
        self._pegar_recortado(lienzo, logo, 931, -49)

    @staticmethod
    def _pegar_recortado(lienzo: Image.Image, imagen: Image.Image, x: int, y: int) -> None:
        """Paste `imagen` at (x, y) even when it overhangs the canvas edge."""
        capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        capa.paste(imagen, (x, y))
        lienzo.alpha_composite(capa)

    def _titular(self, draw: ImageDraw.ImageDraw, antetitulo: str, titular: str) -> None:
        tamano = _TITULAR_TAMANO_MAX
        while True:
            cuerpo = _TITULAR_ESCALA * tamano
            fuente = _fuente("Anton-Regular.ttf", cuerpo)
            tracking = _TITULAR_TRACKING * cuerpo
            lineas = [
                (linea, 1.0) for linea in _envolver(titular, fuente, tracking, _TITULAR_ANCHO)
            ]
            if antetitulo:
                lineas.insert(0, (antetitulo, _ANTETITULO_FACTOR))
            alto = sum(cuerpo * factor * _TITULAR_INTERLINEA for _, factor in lineas)
            cabe = alto <= _TITULAR_ALTO_MAX and (len(lineas) <= (4 if antetitulo else 3))
            if cabe or tamano <= _TITULAR_TAMANO_MIN:
                break
            tamano -= 1

        y = _TITULAR_BASE_Y - alto
        for texto, factor in lineas:
            tam = cuerpo * factor
            fuente_linea = _fuente("Anton-Regular.ttf", tam)
            tracking_linea = _TITULAR_TRACKING * tam
            y += tam * _TITULAR_INTERLINEA
            x = (_ANCHO - _ancho(texto, fuente_linea, tracking_linea)) / 2
            baseline = y - tam * 0.2
            _dibujar(
                draw,
                x + _SOMBRA[0],
                baseline + _SOMBRA[1],
                texto,
                fuente_linea,
                _NEGRO,
                tracking_linea,
            )
            _dibujar(draw, x, baseline, texto, fuente_linea, _BLANCO, tracking_linea)

    def _pie(self, lienzo: Image.Image, draw: ImageDraw.ImageDraw) -> None:
        fuente = _fuente("Montserrat.ttf", 22.0, 700)
        _dibujar(draw, 36, 1316, "www.portalvallenato.com", fuente, _BLANCO, 0)
        hashtag = "#portalvallenato"
        _dibujar(draw, 861.5 - _ancho(hashtag, fuente, 0), 1316, hashtag, fuente, _BLANCO, 0)
        for nombre, x in (("facebook", 895.7), ("instagram", 952.7), ("twitter", 1008.6)):
            icono = Image.open(_ASSETS / f"icon-{nombre}.png").convert("RGBA")
            lienzo.alpha_composite(icono, (round(x) - 2, 1288 - 2))

    def _circulo(self, lienzo: Image.Image, imagen: Image.Image) -> None:
        d = _CIRCULO_DIAMETRO
        cx, cy = _CIRCULO_CENTRO
        foto = _cubrir(imagen, d, d, 0.5, 0.35).convert("RGBA")
        mascara = Image.new("L", (d * 4, d * 4), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
        foto.putalpha(mascara.resize((d, d), Image.LANCZOS))
        # Sombra suave debajo, como en la plantilla.
        sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        ImageDraw.Draw(sombra).ellipse(
            (cx - d / 2 + 4, cy - d / 2 + 8, cx + d / 2 + 4, cy + d / 2 + 8), fill=(0, 0, 0, 90)
        )
        lienzo.alpha_composite(sombra)
        lienzo.alpha_composite(foto, (round(cx - d / 2), round(cy - d / 2)))
        borde = Image.new("RGBA", (d * 4, d * 4), (0, 0, 0, 0))
        b = _CIRCULO_BORDE * 4
        ImageDraw.Draw(borde).ellipse(
            (0, 0, d * 4 - 1, d * 4 - 1), outline=(*_CIRCULO_COLOR_BORDE, 255), width=b
        )
        lienzo.alpha_composite(
            borde.resize((d, d), Image.LANCZOS), (round(cx - d / 2), round(cy - d / 2))
        )
        self._flecha(lienzo)

    def _flecha(self, lienzo: Image.Image) -> None:
        """White curved arrow from the main photo toward the circle."""
        escala = 4
        capa = Image.new("RGBA", (_ANCHO * escala, _ALTO * escala), (0, 0, 0, 0))
        draw = ImageDraw.Draw(capa)
        p0, p1, p2, p3 = (373, 617), (373, 748), (470, 792), (598, 790)
        puntos = []
        for i in range(61):
            t = i / 60
            x = (
                (1 - t) ** 3 * p0[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                (1 - t) ** 3 * p0[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * p3[1]
            )
            puntos.append((x * escala, y * escala))
        grosor = 8 * escala
        draw.line(puntos, fill=_BLANCO, width=grosor, joint="curve")
        for px, py in (puntos[0], puntos[-1]):
            draw.ellipse(
                (px - grosor / 2, py - grosor / 2, px + grosor / 2, py + grosor / 2), fill=_BLANCO
            )
        # Punta: dos trazos hacia atrás desde el final, siguiendo la tangente.
        (x2, y2), (x1, y1) = puntos[-1], puntos[-6]
        ang = math.atan2(y2 - y1, x2 - x1)
        largo = 46 * escala
        for desvio in (math.radians(32), -math.radians(32)):
            ex = x2 - largo * math.cos(ang + desvio)
            ey = y2 - largo * math.sin(ang + desvio)
            draw.line((x2, y2, ex, ey), fill=_BLANCO, width=grosor)
            draw.ellipse(
                (ex - grosor / 2, ey - grosor / 2, ex + grosor / 2, ey + grosor / 2), fill=_BLANCO
            )
        lienzo.alpha_composite(capa.resize((_ANCHO, _ALTO), Image.LANCZOS))
