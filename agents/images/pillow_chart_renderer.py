"""Social-media cards for the weekly Chart Vallenato, drawn with Pillow.

Two cards per edition (the cover with the #1, and the Top 10 list) in two
formats: feed 4:5 (1080x1350) and story 9:16 (1080x1920). They reuse the look of
the "Formato 4:5 portal vallenato" template (black label box, hashtag, round
logo, blue footer with the social icons) and the bundled open-source fonts, so
the result is identical every Saturday and never depends on the server's fonts.

Pure rendering: the caller hands over the rows with their pictures already
downloaded (see `descarga_imagenes`); a missing picture becomes initials.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError

from agents.images.pillow_portada_renderer import (
    _ASSETS,
    _AZUL,
    _BLANCO,
    _NEGRO,
    _ancho,
    _dibujar,
    _fuente,
    _limpiar,
)

Formato = Literal["feed", "historia"]
Lamina = Literal["portada", "lista"]

_ANCHO = 1080
_ALTOS: dict[str, int] = {"feed": 1350, "historia": 1920}
# Instagram/Facebook stories cover the top and bottom of the screen with their own UI.
_MARGEN_SUPERIOR = {"feed": 0, "historia": 150}
_MARGEN_INFERIOR = {"feed": 0, "historia": 200}

_FONDO_ARRIBA = (9, 18, 44)
_FONDO_ABAJO = (30, 50, 105)
_CLARO = (176, 196, 235)
_VERDE, _ROJO, _AMBAR, _GRIS = (52, 211, 110), (255, 99, 88), (240, 180, 20), (140, 155, 185)

_MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


class ChartImagenError(ValueError):
    """The card cannot be drawn (no rows, unreadable picture handled internally)."""


@dataclass(frozen=True, slots=True)
class FilaImagen:
    posicion: int
    titulo: str
    artista: str | None
    vistas_semana: int
    tendencia: str | None = None  # sube | baja | igual | nuevo
    foto_artista: bytes | None = None
    miniatura: bytes | None = None


def _rango_semana(semana_fin: date) -> str:
    inicio = semana_fin - timedelta(days=6)
    if inicio.month == semana_fin.month:
        return f"{inicio.day} al {semana_fin.day} de {_MESES[semana_fin.month - 1]}"
    return (
        f"{inicio.day} de {_MESES[inicio.month - 1]} al {semana_fin.day} "
        f"de {_MESES[semana_fin.month - 1]}"
    )


def _vistas(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".replace(".", ",") + " M"
    if n >= 10_000:
        return f"{round(n / 1000)} mil"
    if n >= 1000:
        return f"{n / 1000:.1f}".replace(".", ",") + " mil"
    return str(n)


def _abrir(datos: bytes | None) -> Image.Image | None:
    if not datos:
        return None
    try:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(datos))).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None


def _recortar(texto: str, fuente: ImageFont.FreeTypeFont, ancho_max: float) -> str:
    if fuente.getlength(texto) <= ancho_max:
        return texto
    while texto and fuente.getlength(texto + "…") > ancho_max:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _lineas(
    texto: str, fuente: ImageFont.FreeTypeFont, ancho_max: float, max_lineas: int
) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if actual and fuente.getlength(prueba) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = _recortar(lineas[-1] + " …", fuente, ancho_max)
    return [_recortar(linea, fuente, ancho_max) for linea in lineas]


def _texto(
    draw: ImageDraw.ImageDraw,
    x: float,
    base: float,
    texto: str,
    fuente: ImageFont.FreeTypeFont,
    color: tuple[int, ...],
    alinear: str = "l",
) -> None:
    ancho = fuente.getlength(texto)
    if alinear == "r":
        x -= ancho
    elif alinear == "c":
        x -= ancho / 2
    draw.text((x, base), texto, font=fuente, fill=color, anchor="ls")


def _fondo(ancho: int, alto: int) -> Image.Image:
    mascara = Image.linear_gradient("L").resize((ancho, alto))
    lienzo = Image.composite(
        Image.new("RGB", (ancho, alto), _FONDO_ABAJO),
        Image.new("RGB", (ancho, alto), _FONDO_ARRIBA),
        mascara,
    ).convert("RGBA")
    # Soft blue glow behind the headline, like the template's gradient.
    brillo = Image.new("RGBA", (ancho // 4, alto // 4), (0, 0, 0, 0))
    ImageDraw.Draw(brillo).ellipse(
        (ancho // 4 * 0.35, -alto // 14, ancho // 4 * 1.2, alto // 4 * 0.42), fill=(*_AZUL, 140)
    )
    brillo = brillo.filter(ImageFilter.GaussianBlur(28)).resize((ancho, alto), Image.LANCZOS)
    lienzo.alpha_composite(brillo)
    return lienzo


def _imagen_circulo(f: FilaImagen) -> tuple[Image.Image | None, float]:
    """The artist's photo; when the website has none, the centre of the video's thumbnail.

    Returns the picture and the vertical focus for the crop (faces sit high in portraits,
    a thumbnail is best cropped from its middle).
    """
    foto = _abrir(f.foto_artista)
    if foto is not None:
        return foto, 0.3
    return _abrir(f.miniatura), 0.5


def _bloque_video(f: FilaImagen, w: int, h: int) -> Image.Image:
    """The video's thumbnail as a rounded 16:9 block (artist photo, then initials, if missing)."""
    s = 4
    imagen = _abrir(f.miniatura) or _abrir(f.foto_artista)
    if imagen is not None:
        base = ImageOps.fit(imagen, (w * s, h * s), Image.LANCZOS, centering=(0.5, 0.4)).convert(
            "RGBA"
        )
    else:
        base = Image.new("RGBA", (w * s, h * s), (*_AZUL, 255))
        iniciales = "".join(p[0] for p in _limpiar(f.artista or "").split()[:2]) or "PV"
        ImageDraw.Draw(base).text(
            (w * s / 2, h * s / 2),
            iniciales,
            font=_fuente("Anton-Regular.ttf", h * s * 0.5),
            fill=_BLANCO,
            anchor="mm",
        )
    mascara = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w * s - 1, h * s - 1), 10 * s, fill=255)
    base.putalpha(mascara)
    anillo = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(anillo).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), 10 * s, outline=(*_BLANCO, 255), width=3 * s
    )
    base.alpha_composite(anillo)
    return base.resize((w, h), Image.LANCZOS)


def _circulo_foto(
    foto: Image.Image | None, nombre: str, d: int, borde: int = 0, enfoque_y: float = 0.3
) -> Image.Image:
    """Round picture (initials on brand blue when there is no picture at all)."""
    s = 4
    if foto is not None:
        recorte = ImageOps.fit(foto, (d * s, d * s), Image.LANCZOS, centering=(0.5, enfoque_y))
        recorte = recorte.convert("RGBA")
    else:
        recorte = Image.new("RGBA", (d * s, d * s), (*_AZUL, 255))
        iniciales = "".join(p[0] for p in _limpiar(nombre).split()[:2]) or "PV"
        fuente = _fuente("Anton-Regular.ttf", d * s * 0.42)
        ImageDraw.Draw(recorte).text(
            (d * s / 2, d * s / 2), iniciales, font=fuente, fill=_BLANCO, anchor="mm"
        )
    mascara = Image.new("L", (d * s, d * s), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, d * s - 1, d * s - 1), fill=255)
    recorte.putalpha(mascara)
    if borde:
        anillo = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
        ImageDraw.Draw(anillo).ellipse(
            (0, 0, d * s - 1, d * s - 1), outline=(*_BLANCO, 255), width=borde * s
        )
        recorte.alpha_composite(anillo)
    return recorte.resize((d, d), Image.LANCZOS)


def _flecha(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, tendencia: str | None
) -> None:
    if tendencia == "sube":
        draw.polygon([(cx, cy - r), (cx + r, cy + r * 0.8), (cx - r, cy + r * 0.8)], fill=_VERDE)
    elif tendencia == "baja":
        draw.polygon([(cx, cy + r), (cx + r, cy - r * 0.8), (cx - r, cy - r * 0.8)], fill=_ROJO)
    elif tendencia == "nuevo":
        fuente = _fuente("Montserrat.ttf", r * 1.25, 800)
        draw.text((cx, cy), "NEW", font=fuente, fill=_AMBAR, anchor="mm")
    else:
        draw.rectangle((cx - r * 0.8, cy - r * 0.18, cx + r * 0.8, cy + r * 0.18), fill=_GRIS)


class PillowChartRenderer:
    """Draws the cover and the Top 10 card of a weekly edition."""

    def renderizar(
        self,
        semana_fin: date,
        filas: list[FilaImagen],
        *,
        lamina: Lamina,
        formato: Formato = "feed",
        marca_agua: str | None = None,
    ) -> bytes:
        if not filas:
            raise ChartImagenError("La edición no tiene filas")
        alto = _ALTOS[formato]
        lienzo = _fondo(_ANCHO, alto)
        draw = ImageDraw.Draw(lienzo)
        sup, inf = _MARGEN_SUPERIOR[formato], _MARGEN_INFERIOR[formato]
        self._cabecera(lienzo, draw, sup)
        y0 = 105 + sup
        y1 = alto - inf - 62 - 24
        if lamina == "portada":
            self._portada(lienzo, draw, semana_fin, filas, y0, y1, formato)
        else:
            self._lista(lienzo, draw, semana_fin, filas[:10], y0, y1)
        if marca_agua:
            self._marca_agua(lienzo, marca_agua)
        self._pie(lienzo, draw, alto - 1350 - inf)
        salida = io.BytesIO()
        lienzo.convert("RGB").save(salida, "PNG", optimize=True)
        return salida.getvalue()

    @staticmethod
    def _marca_agua(lienzo: Image.Image, texto: str) -> None:
        """Big diagonal banner so a preview can never be mistaken for the real card."""
        fuente = _fuente("Anton-Regular.ttf", 120)
        caja = fuente.getbbox(texto)
        ancho, alto = caja[2] - caja[0] + 80, caja[3] - caja[1] + 60
        capa = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.rectangle((0, 0, ancho, alto), fill=(0, 0, 0, 110))
        d.text((ancho / 2, alto / 2), texto, font=fuente, fill=(255, 255, 255, 150), anchor="mm")
        capa = capa.rotate(24, expand=True, resample=Image.BICUBIC)
        lienzo.alpha_composite(
            capa, (round((lienzo.width - capa.width) / 2), round((lienzo.height - capa.height) / 2))
        )

    # --- marco de la plantilla ------------------------------------------------

    def _cabecera(self, lienzo: Image.Image, draw: ImageDraw.ImageDraw, dy: int) -> None:
        fuente = _fuente("Montserrat-Italic.ttf", 33, 700)
        etiqueta = "RADAR VALLENATO"
        ancho = _ancho(etiqueta, fuente, 0.17)
        draw.rectangle((0, 7.4 + dy, 14 + ancho + 26, 81.8 + dy), fill=_NEGRO)
        _dibujar(draw, 14, 56.5 + dy, etiqueta, fuente, _BLANCO, 0.17)
        fuente = _fuente("Montserrat.ttf", 36, 300)
        hashtag = "#NoticiasDelVallenato"
        _dibujar(
            draw, 930.4 - _ancho(hashtag, fuente, -1.5), 58 + dy, hashtag, fuente, _BLANCO, -1.5
        )
        logo = Image.open(_ASSETS / "logo-pv-original.png").convert("RGBA")
        logo = logo.resize((186, 186), Image.LANCZOS).rotate(1, resample=Image.BICUBIC)
        capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        capa.paste(logo, (931, -49 + dy))
        lienzo.alpha_composite(capa)

    def _pie(self, lienzo: Image.Image, draw: ImageDraw.ImageDraw, dy: int) -> None:
        fuente = _fuente("Montserrat.ttf", 22.0, 700)
        _dibujar(draw, 36, 1316 + dy, "www.portalvallenato.com", fuente, _BLANCO, 0)
        hashtag = "#portalvallenato"
        _dibujar(draw, 861.5 - _ancho(hashtag, fuente, 0), 1316 + dy, hashtag, fuente, _BLANCO, 0)
        for nombre, x in (("facebook", 895.7), ("instagram", 952.7), ("twitter", 1008.6)):
            icono = Image.open(_ASSETS / f"icon-{nombre}.png").convert("RGBA")
            lienzo.alpha_composite(icono, (round(x) - 2, 1288 - 2 + dy))

    # --- láminas -------------------------------------------------------------

    def _portada(
        self,
        lienzo: Image.Image,
        draw: ImageDraw.ImageDraw,
        semana_fin: date,
        filas: list[FilaImagen],
        y0: int,
        y1: int,
        formato: Formato,
    ) -> None:
        top = filas[0]
        tw = 800 if formato == "feed" else 936
        th = round(tw * 9 / 16)
        pildora, titular, bloque, fila_h = 52, 208, 170, 86
        resto = fila_h * min(len(filas) - 1, 2)
        base = pildora + titular + th + bloque + resto
        libre = max((y1 - y0) - base - 22 - 30 - 24 - 24, 0)
        hueco = libre / 5
        y = float(y0)

        # Week pill.
        fuente = _fuente("Montserrat.ttf", 27, 700)
        texto = f"SEMANA DEL {_rango_semana(semana_fin).upper()}"
        ancho = fuente.getlength(texto) + 56
        x = (_ANCHO - ancho) / 2
        draw.rounded_rectangle((x, y, x + ancho, y + pildora), radius=26, fill=_AZUL)
        _texto(draw, _ANCHO / 2, y + pildora / 2 + 10, texto, fuente, _BLANCO, "c")
        y += pildora + 22 + hueco

        # Headline.
        for linea, color in (("LO MÁS ESCUCHADO", _BLANCO), ("DE LA SEMANA", (120, 160, 235))):
            fuente = _fuente("Anton-Regular.ttf", 96)
            y += 104
            _texto(draw, _ANCHO / 2 + 5, y - 20 + 5, linea, fuente, _NEGRO, "c")
            _texto(draw, _ANCHO / 2, y - 20, linea, fuente, color, "c")
        y += 30 + hueco

        # #1: video thumbnail, number badge and artist circle.
        x_img = (_ANCHO - tw) / 2
        miniatura = _abrir(top.miniatura)
        if miniatura is not None:
            bloque_img = ImageOps.fit(miniatura, (tw, th), Image.LANCZOS)
        else:
            bloque_img = Image.new("RGB", (tw, th), _AZUL)
        marco = Image.new("RGBA", (tw + 16, th + 16), (*_BLANCO, 255))
        marco.paste(bloque_img, (8, 8))
        lienzo.alpha_composite(marco, (round(x_img) - 8, round(y) - 8))
        draw.rectangle((x_img - 8, y - 8, x_img + 104, y + 132), fill=_NEGRO)
        _texto(draw, x_img + 48, y + 112, "1", _fuente("Anton-Regular.ttf", 128), _BLANCO, "c")
        d = 230
        foto, enfoque = _imagen_circulo(top)
        circulo = _circulo_foto(
            foto, top.artista or "Portal Vallenato", d, borde=8, enfoque_y=enfoque
        )
        sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        cx, cy = min(round(x_img + tw - d / 2 - 30), _ANCHO - d - 24), round(y + th - d / 2 + 24)
        ImageDraw.Draw(sombra).ellipse(
            (cx + 4, cy + 10, cx + d + 4, cy + d + 10), fill=(0, 0, 0, 100)
        )
        lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(6)))
        lienzo.alpha_composite(circulo, (cx, cy))
        y += th + 24 + hueco

        # #1 text (left of the circle).
        ancho_txt = tw - d - 10
        nombre = _limpiar(top.artista or "")
        fuente = _fuente("Anton-Regular.ttf", 56)
        if nombre:
            y += 50
            _texto(draw, x_img, y, _recortar(nombre, fuente, ancho_txt), fuente, _BLANCO)
        fuente = _fuente("Montserrat.ttf", 27, 700)
        for linea in _lineas(top.titulo, fuente, ancho_txt, 2):
            y += 36
            _texto(draw, x_img, y, linea, fuente, _CLARO)
        y += 38
        _texto(
            draw,
            x_img,
            y,
            f"{_vistas(top.vistas_semana)} vistas esta semana",
            _fuente("Montserrat.ttf", 25, 700),
            (120, 160, 235),
        )
        y += 24 + hueco

        # #2 and #3.
        for fila in filas[1:3]:
            self._fila(lienzo, draw, fila, x_img - 8, y, tw + 16, fila_h, banda=fila.posicion == 2)
            y += fila_h

    def _lista(
        self,
        lienzo: Image.Image,
        draw: ImageDraw.ImageDraw,
        semana_fin: date,
        filas: list[FilaImagen],
        y0: int,
        y1: int,
    ) -> None:
        y = y0 + 90
        fuente = _fuente("Anton-Regular.ttf", 92)
        _texto(draw, 41, y + 5, "TOP 10 DE LA SEMANA", fuente, _NEGRO)
        _texto(draw, 36, y, "TOP 10 DE LA SEMANA", fuente, _BLANCO)
        fuente = _fuente("Montserrat.ttf", 27, 700)
        y += 50
        _texto(draw, 36, y, f"DEL {_rango_semana(semana_fin).upper()}", fuente, (120, 160, 235))
        y += 28
        fila_h = min((y1 - y) / max(len(filas), 1), 150)
        for i, fila in enumerate(filas):
            self._fila(lienzo, draw, fila, 0, y + i * fila_h, _ANCHO, fila_h, banda=i % 2 == 0)

    def _fila(
        self,
        lienzo: Image.Image,
        draw: ImageDraw.ImageDraw,
        f: FilaImagen,
        x0: float,
        y: float,
        w: float,
        h: float,
        *,
        banda: bool,
    ) -> None:
        if banda:
            capa = Image.new("RGBA", (round(w), round(h)), (255, 255, 255, 18))
            lienzo.alpha_composite(capa, (round(x0), round(y)))
        centro = y + h / 2
        bw = h * 0.72
        x = x0 + 36
        draw.rectangle((x, centro - (h - 18) / 2, x + bw, centro + (h - 18) / 2), fill=_AZUL)
        _texto(
            draw, x + bw / 2, centro + h * 0.2, str(f.posicion),
            _fuente("Anton-Regular.ttf", h * 0.58), _BLANCO, "c",
        )  # fmt: skip
        th = round(h - 18)
        tw = round(th * 16 / 9)
        x += bw + 16
        lienzo.alpha_composite(_bloque_video(f, tw, th), (round(x), round(centro - th / 2)))
        if f.posicion <= 3:  # the top 3 also get the artist's photo, small, on the corner
            ds = round(h * 0.52)
            lienzo.alpha_composite(
                _circulo_foto(_abrir(f.foto_artista), f.artista or "Portal Vallenato", ds, borde=3),
                (round(x + tw - ds * 0.6), round(centro + th / 2 - ds * 0.9)),
            )
        x += tw + 26
        x_der = x0 + w - 36
        ancho_txt = x_der - 190 - x
        nombre = _limpiar(f.artista or "")
        if nombre:
            fuente = _fuente("Anton-Regular.ttf", h * 0.37)
            _texto(
                draw, x, centro - h * 0.02, _recortar(nombre, fuente, ancho_txt), fuente, _BLANCO
            )
            fuente = _fuente("Montserrat.ttf", h * 0.225, 600)
            _texto(
                draw, x, centro + h * 0.28, _recortar(f.titulo, fuente, ancho_txt), fuente, _CLARO
            )
        else:
            fuente = _fuente("Montserrat.ttf", h * 0.26, 700)
            _texto(
                draw, x, centro + h * 0.09, _recortar(f.titulo, fuente, ancho_txt), fuente, _BLANCO
            )
        _texto(
            draw, x_der - 50, centro + h * 0.04, _vistas(f.vistas_semana),
            _fuente("Montserrat.ttf", h * 0.27, 800), _BLANCO, "r",
        )  # fmt: skip
        _texto(
            draw, x_der - 50, centro + h * 0.27, "vistas",
            _fuente("Montserrat.ttf", h * 0.17, 500), _GRIS, "r",
        )  # fmt: skip
        _flecha(draw, x_der - 16, centro, h * 0.11, f.tendencia)
