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

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError

from core.entities.colores_marca import ColoresMarca
from core.ports.portada_renderer import PortadaError, SolicitudPortada, VariantePortada

_ASSETS = Path(__file__).parent / "assets"

_ANCHO, _ALTO = 1080, 1350
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

# Layout with a hook (`antetitulo`), approved 2026-11-26: the hook on one line
# inside a yellow button, and a smaller white headline over the site's menu blue.
# Colours come from `ColoresMarca` (by default, portalvallenato.com's).
# `_GANCHO_ALTO_MAX` keeps the whole block below the highlight circle.
_GANCHO_ANCHO = 940
_GANCHO_BASE_Y = 1250
_GANCHO_ALTO_MAX = 270
_GANCHO_TAMANO_MAX = 92
_GANCHO_CAJA_ALTO = 1.34  # times the font size
_GANCHO_CAJA_LINEA_BASE = 1.10
_GANCHO_CAJA_MARGEN = 30
_GANCHO_CAJA_RADIO = 14
_GANCHO_CAJA_SEPARACION = 18
_GANCHO_TITULAR_ANCHO = 1000
_GANCHO_TITULAR_TAMANO_MAX = 54
_GANCHO_TITULAR_TAMANO_COMODO = 40
_GANCHO_TITULAR_INTERLINEA = 1.14
_GANCHO_GRAD = (835, 470)  # inicio y largo del degradado

# A quoted name up to this long ("‘LINDA REMIX’") is never split across lines.
_CITA_MAX_CARACTERES = 24
_CITA = re.compile("[‘“\"'][^‘’“”\"']+[’”\"']")
_ESPACIO_FIJO = "\u00a0"

# Highlight circle (template page 3/4).
_CIRCULO_CENTRO = (814, 772)
_CIRCULO_DIAMETRO = 391
_CIRCULO_BORDE = 8
_CIRCULO_COLOR_BORDE = (0xF9, 0xEB, 0xE9)

_ETIQUETAS = {
    VariantePortada.NOTICIAS: "NOTICIAS",
    VariantePortada.LO_ULTIMO: "LO ÚLTIMO",
    VariantePortada.DE_INTERES: "DE INTERÉS",
    VariantePortada.MEMES: "MEMES",
    VariantePortada.DE_OPINION: "DE OPINIÓN",
}

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
    color: tuple[int, ...],
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


def _cubrir(
    imagen: Image.Image, ancho: int, alto: int, fx: float, fy: float, zoom: float = 1.0
) -> Image.Image:
    """Scale-and-crop `imagen` to fill `ancho`x`alto`, keeping the (fx, fy) focus."""
    w = min(imagen.width, imagen.height * ancho / alto) / max(zoom, 1.0)
    h = w * alto / ancho
    x = max(imagen.width - w, 0) * fx
    y = max(imagen.height - h, 0) * fy
    caja = (x, y, min(x + w, imagen.width), min(y + h, imagen.height))
    return imagen.resize((ancho, alto), Image.LANCZOS, box=caja)


def _abrir(datos: bytes, nombre: str) -> Image.Image:
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen = ImageOps.exif_transpose(imagen)
        return imagen.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PortadaError(f"No se pudo leer la {nombre}: {exc}") from exc


def _degradado(color: tuple[int, int, int], inicio: int, largo: int) -> Image.Image:
    capa = Image.new("RGBA", (_ANCHO, _ALTO), (*color, 0))
    px = capa.load()
    for y in range(_ALTO):
        t = min(max((y - inicio) / largo, 0.0), 1.0)
        alfa = int(255 * (1 - (1 - t) ** _GRAD_CAPAS))
        if alfa:
            for x in range(_ANCHO):
                px[x, y] = (*color, alfa)
    return capa


def _envolver(
    texto: str, fuente: ImageFont.FreeTypeFont, tracking: float, ancho_max: float
) -> list[str]:
    lineas: list[str] = []
    actual = ""
    for palabra in texto.split(" "):
        prueba = f"{actual} {palabra}".strip(" ")
        if actual and _ancho(prueba, fuente, tracking) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def _unir_citas(texto: str) -> str:
    """Glue the words of a short quoted name so the wrap keeps them together."""

    def unir(cita: re.Match[str]) -> str:
        frase = cita.group(0)
        if len(frase) > _CITA_MAX_CARACTERES:
            return frase
        return frase.replace(" ", _ESPACIO_FIJO)

    return _CITA.sub(unir, texto)


def _limpiar(texto: str) -> str:
    return " ".join(_EMOJI.sub("", texto).split()).upper()


def _rgb(color: str) -> tuple[int, int, int]:
    """`#RRGGBB` as an RGB tuple."""
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


class PillowPortadaRenderer:
    """`PortadaRenderer` implemented with Pillow."""

    def __init__(self, colores: ColoresMarca | None = None) -> None:
        colores = colores or ColoresMarca()
        self._color_fondo = _rgb(colores.fondo)
        self._color_destacado = _rgb(colores.destacado)
        self._color_texto_destacado = _rgb(colores.texto_destacado)

    def renderizar(self, solicitud: SolicitudPortada, *, formato: str = "png") -> bytes:
        titular = _limpiar(solicitud.titular)
        antetitulo = _limpiar(solicitud.antetitulo) if solicitud.antetitulo else ""
        if not titular:
            raise PortadaError("El titular no puede estar vacío")

        base = _abrir(solicitud.imagen_base, "imagen base")
        lienzo = _cubrir(
            base, _ANCHO, _ALTO, solicitud.enfoque_x, solicitud.enfoque_y, solicitud.zoom
        )
        lienzo = lienzo.convert("RGBA")
        geometria = _GANCHO_GRAD if antetitulo else (_GRAD_INICIO, _GRAD_LARGO)
        lienzo.alpha_composite(_degradado(self._color_fondo, *geometria))

        if solicitud.imagen_circulo is not None:
            self._circulo(lienzo, _abrir(solicitud.imagen_circulo, "imagen del círculo"))

        draw = ImageDraw.Draw(lienzo)
        self._cabecera(lienzo, draw, solicitud.variante)
        if antetitulo:
            self._gancho_y_titular(draw, antetitulo, titular)
        else:
            self._titular(draw, titular)
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
        x_hashtag = 930.4 - _ancho(hashtag, fuente, tracking)
        # Soft dark halo (not in the Canva template): without it the thin white
        # hashtag disappears over light photos.
        halo = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        _dibujar(ImageDraw.Draw(halo), x_hashtag, 60, hashtag, fuente, (0, 0, 0, 170), tracking)
        lienzo.alpha_composite(halo.filter(ImageFilter.GaussianBlur(3)))
        _dibujar(draw, x_hashtag, 58, hashtag, fuente, _BLANCO, tracking)

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

    def _titular(self, draw: ImageDraw.ImageDraw, titular: str) -> None:
        tamano = _TITULAR_TAMANO_MAX
        while True:
            cuerpo = _TITULAR_ESCALA * tamano
            fuente = _fuente("Anton-Regular.ttf", cuerpo)
            tracking = _TITULAR_TRACKING * cuerpo
            lineas = _envolver(titular, fuente, tracking, _TITULAR_ANCHO)
            alto = len(lineas) * cuerpo * _TITULAR_INTERLINEA
            cabe = alto <= _TITULAR_ALTO_MAX and len(lineas) <= 3
            if cabe or tamano <= _TITULAR_TAMANO_MIN:
                break
            tamano -= 1

        y = _TITULAR_BASE_Y - alto
        for texto in lineas:
            y += cuerpo * _TITULAR_INTERLINEA
            self._linea_centrada(draw, texto, cuerpo, y - cuerpo * 0.2, _BLANCO, _SOMBRA)

    def _gancho_y_titular(self, draw: ImageDraw.ImageDraw, gancho: str, titular: str) -> None:
        # El gancho va siempre en una línea: se reduce hasta caber.
        tam_gancho = _GANCHO_TAMANO_MAX
        while True:
            fuente = _fuente("Anton-Regular.ttf", tam_gancho)
            ancho_gancho = _ancho(gancho, fuente, _TITULAR_TRACKING * tam_gancho)
            if ancho_gancho <= _GANCHO_ANCHO or tam_gancho <= 1:
                break
            tam_gancho -= 1
        alto_caja = tam_gancho * _GANCHO_CAJA_ALTO
        alto_gancho = alto_caja + _GANCHO_CAJA_SEPARACION

        # El titular prefiere dos líneas; si es muy largo usa más, cada vez menores.
        titular = _unir_citas(titular)
        tam = _GANCHO_TITULAR_TAMANO_MAX
        while True:
            fuente = _fuente("Anton-Regular.ttf", tam)
            lineas = _envolver(titular, fuente, _TITULAR_TRACKING * tam, _GANCHO_TITULAR_ANCHO)
            alto = alto_gancho + len(lineas) * tam * _GANCHO_TITULAR_INTERLINEA
            comodo = len(lineas) <= 2 or tam <= _GANCHO_TITULAR_TAMANO_COMODO
            if (alto <= _GANCHO_ALTO_MAX and comodo) or tam <= 20:
                break
            tam -= 1

        y = _GANCHO_BASE_Y - alto
        x = (_ANCHO - ancho_gancho) / 2 - _GANCHO_CAJA_MARGEN
        draw.rounded_rectangle(
            (x, y, _ANCHO - x, y + alto_caja), radius=_GANCHO_CAJA_RADIO, fill=self._color_destacado
        )
        base = y + tam_gancho * _GANCHO_CAJA_LINEA_BASE
        self._linea_centrada(draw, gancho, tam_gancho, base, self._color_texto_destacado, None)
        y += alto_gancho
        sombra = (round(_SOMBRA[0] * 0.7), round(_SOMBRA[1] * 0.7))
        for linea in lineas:
            texto = linea.replace(_ESPACIO_FIJO, " ")
            self._linea_centrada(draw, texto, tam, y + tam * 0.9, _BLANCO, sombra)
            y += tam * _GANCHO_TITULAR_INTERLINEA

    @staticmethod
    def _linea_centrada(
        draw: ImageDraw.ImageDraw,
        texto: str,
        tamano: float,
        baseline: float,
        color: tuple[int, int, int],
        sombra: tuple[int, int] | None,
    ) -> None:
        fuente = _fuente("Anton-Regular.ttf", tamano)
        tracking = _TITULAR_TRACKING * tamano
        x = (_ANCHO - _ancho(texto, fuente, tracking)) / 2
        if sombra is not None:
            dx, dy = sombra
            _dibujar(draw, x + dx, baseline + dy, texto, fuente, _NEGRO, tracking)
        _dibujar(draw, x, baseline, texto, fuente, color, tracking)

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
