"""Renders a Pauta's closing report as a client-facing PDF.

Sprint — Configuración de identidad comercial + reporte PDF de contrato.
Deliberately outside `core/services/` — building bytes with a third-party
layout library (`reportlab`) is presentation/infrastructure, not domain
logic (see `core/services/README.md`, "Qué NO vive aquí"). This module
only *renders* a `core.services.reporte_service.ReportePauta` that was
already built purely from domain data — it never recomputes cuota,
vigencia, or which solicitudes count as "consumidas".

Dates on `Pauta` (`fecha_inicio`/`fecha_fin`) are plain `date` — no
timezone conversion needed. Dates coming from `PublicationRequest`/
`DestinoPublicacion` are UTC `datetime` and are shown converted to
America/Bogota, the same business-timezone convention
`frontend/src/lib/format.ts::formatFechaHoraNegocio` already applies —
otherwise a publication made late at night could print as the wrong day.
"""

from __future__ import annotations

import functools
import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape as _xml_escape
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from PIL.ImageDraw import ImageDraw

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.identidad_comercial import IdentidadComercial
from core.entities.pauta import PautaTipo
from core.services.reporte_service import ReportePauta, ReporteSolicitud

_TZ_NEGOCIO = ZoneInfo("America/Bogota")

_PAUTA_TIPO_LABELS = {
    PautaTipo.INDIVIDUAL: "Individual",
    PautaTipo.MENSUAL: "Mensual",
    PautaTipo.BIMESTRAL: "Bimestral",
    PautaTipo.TRIMESTRAL: "Trimestral",
    PautaTipo.SEMESTRAL: "Semestral",
    PautaTipo.ANUAL: "Anual",
}

_CANAL_LABELS = {
    CanalPublicacion.WORDPRESS: "Página web",
    CanalPublicacion.FACEBOOK: "Facebook",
    CanalPublicacion.INSTAGRAM: "Instagram",
}

_HEX_ENLACE = "#1a73e8"
_COLOR_GRIS = colors.HexColor("#666666")
_COLOR_BORDE = colors.HexColor("#dddddd")
_COLOR_FONDO_ENCABEZADO = colors.HexColor("#f2f2f2")
_URL_ABSOLUTA = re.compile(r"^https?://", re.IGNORECASE)
_NOMBRE_SISTEMA = "Portal Vallenato Newsroom"


def _escape(texto: str) -> str:
    return _xml_escape(texto)


def _fmt_fecha(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "—"


def _fmt_fecha_negocio(valor: datetime | None) -> str:
    return valor.astimezone(_TZ_NEGOCIO).strftime("%d/%m/%Y") if valor else "—"


def _fmt_moneda(valor: Decimal) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def _titulo_o_fragmento(solicitud: ReporteSolicitud, max_len: int = 60) -> str:
    """Return `solicitud.titulo`, or a fragment of `texto` when there is none.

    `texto` is a required field (never empty — see
    `core.entities.publication_request.PublicationRequest`), so the
    "Publicación" column of the detalle table never renders blank. This is
    real content, not an invented title — same "no inventar" discipline
    the report follows everywhere else, just falling back to a different
    real field instead of a placeholder.
    """
    if solicitud.titulo:
        return _escape(solicitud.titulo)
    texto = solicitud.texto.strip()
    fragmento = texto if len(texto) <= max_len else texto[:max_len].rstrip() + "…"
    return _escape(fragmento)


def _link_texto(href: str, texto: str) -> str:
    """A clickable reportlab inline link showing `texto`, never the raw `href`."""
    href_escapado = _xml_escape(href, {'"': "&quot;"})
    texto_escapado = _escape(texto)
    return (
        f'<link href="{href_escapado}"><u><font color="{_HEX_ENLACE}">'
        f"{texto_escapado}</font></u></link>"
    )


def _enlace_o_guion(url: str | None) -> str:
    if not url:
        return "—"
    visible = url if len(url) <= 42 else url[:39] + "…"
    return _link_texto(url, visible)


def _href_whatsapp(telefono: str) -> str:
    """Build a WhatsApp click-to-chat link — digits only, no `+`, per WhatsApp's
    own `wa.me` spec (a `tel:` link would just open the dialer, not WhatsApp)."""
    return f"https://wa.me/{re.sub(r'[^0-9]', '', telefono)}"


def _href_sitio_web(url: str) -> str:
    url = url.strip()
    return url if _URL_ABSOLUTA.match(url) else f"https://{url}"


def _href_red_social(valor: str, dominio: str) -> str:
    """Build a full profile URL from a handle/path, or pass an already-absolute URL through.

    Lets the operator type either a full link or just `@handle` in
    Instagram/Facebook — the report always ends up with a real, clickable
    URL either way, labeled with the platform's name, never the raw text
    typed into Configuración.
    """
    valor = valor.strip()
    if _URL_ABSOLUTA.match(valor):
        return valor
    return f"https://{dominio}/{valor.lstrip('@')}"


def _partes_otras_redes(texto: str) -> list[tuple[str, str]]:
    """Split "Label: url, Label2: url2" into (label, value) pairs — value is
    the raw remainder after the first `:`, unparsed further."""
    piezas: list[tuple[str, str]] = []
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        label, separador, valor = parte.partition(":")
        piezas.append((label.strip(), valor.strip() if separador else ""))
    return piezas


def _es_tiktok(label: str, valor: str) -> bool:
    return "tiktok" in label.lower() and bool(_URL_ABSOLUTA.match(valor))


def _lineas_otras_redes_sin_iconos(texto: str) -> list[str]:
    """Same as before, but skips whatever `_es_tiktok` already turned into an
    icon — TikTok gets its own badge (see `_lineas_contacto`), everything
    else in this free-text field keeps showing as a clickable link (when the
    value is a URL) or as plain text (no domain guessed for an unknown
    platform)."""
    piezas: list[str] = []
    for label, valor in _partes_otras_redes(texto):
        if _es_tiktok(label, valor):
            continue
        if valor and _URL_ABSOLUTA.match(valor):
            piezas.append(_link_texto(valor, label))
        else:
            piezas.append(_escape(f"{label}: {valor}" if valor else label))
    return piezas


_ICONO_LADO_PX = 128  # supersampled canvas — downscaled for anti-aliased edges
_ICONO_LADO_FINAL_PX = 40
_ICONO_COLOR_FONDO = "#666666"  # mismo gris que styles.contacto — nunca compite con el logo


def _dibujar_globo(draw: ImageDraw, lado: int) -> None:
    """Sitio web: a plain geometric globe — latitude line + meridian ellipse."""
    pad = lado * 0.24
    grosor = max(2, lado // 22)
    draw.ellipse((pad, pad, lado - pad, lado - pad), outline="white", width=grosor)
    cx, cy = lado / 2, lado / 2
    r = (lado - 2 * pad) / 2
    draw.ellipse((cx - r * 0.42, cy - r, cx + r * 0.42, cy + r), outline="white", width=grosor)
    draw.line((cx - r, cy, cx + r, cy), fill="white", width=grosor)


def _dibujar_camara(draw: ImageDraw, lado: int) -> None:
    """Instagram: a rounded camera outline with a lens and a shutter dot."""
    pad = lado * 0.22
    grosor = max(2, lado // 22)
    draw.rounded_rectangle(
        (pad, pad, lado - pad, lado - pad), radius=lado * 0.14, outline="white", width=grosor
    )
    cx, cy = lado / 2, lado / 2
    r = (lado - 2 * pad) * 0.22
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="white", width=grosor)
    punto_r = lado * 0.035
    punto_cx, punto_cy = lado - pad - punto_r * 2.2, pad + punto_r * 2.2
    draw.ellipse(
        (punto_cx - punto_r, punto_cy - punto_r, punto_cx + punto_r, punto_cy + punto_r),
        fill="white",
    )


def _dibujar_nota_musical(draw: ImageDraw, lado: int) -> None:
    """TikTok: a simplified eighth-note glyph — universal "audio/video" mark."""
    grosor = max(2, lado // 20)
    cx, cy = lado * 0.42, lado * 0.64
    r = lado * 0.13
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="white")
    tallo_x = cx + r * 0.92
    draw.line((tallo_x, cy, tallo_x, lado * 0.22), fill="white", width=grosor)
    draw.line(
        (tallo_x, lado * 0.22, tallo_x + lado * 0.16, lado * 0.30), fill="white", width=grosor
    )


def _dibujar_burbuja_chat(draw: ImageDraw, lado: int) -> None:
    """WhatsApp: a filled speech bubble — reads clearly even at badge size,
    unlike a thin handset outline (the previous design, illegible at 40px)."""
    pad = lado * 0.24
    ancho = lado - 2 * pad
    alto = ancho * 0.76
    x0 = pad
    y0 = pad + (lado - 2 * pad - alto) / 2 - lado * 0.03
    x1, y1 = x0 + ancho, y0 + alto
    draw.rounded_rectangle((x0, y0, x1, y1), radius=alto * 0.3, fill="white")
    cola = [
        (x0 + ancho * 0.20, y1 - alto * 0.05),
        (x0 + ancho * 0.20, y1 + alto * 0.32),
        (x0 + ancho * 0.42, y1 - alto * 0.05),
    ]
    draw.polygon(cola, fill="white")


def _dibujar_letra_f(draw: ImageDraw, lado: int) -> None:
    """Facebook: a plain "f" mark — the one glyph safe to render with Pillow's
    built-in scalable default font (no external font file needed)."""
    from PIL import ImageFont

    fuente = ImageFont.load_default(size=int(lado * 0.62))
    caja = draw.textbbox((0, 0), "f", font=fuente)
    ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
    draw.text(
        ((lado - ancho) / 2 - caja[0], (lado - alto) / 2 - caja[1]), "f", font=fuente, fill="white"
    )


_DIBUJANTES = {
    "web": _dibujar_globo,
    "instagram": _dibujar_camara,
    "facebook": _dibujar_letra_f,
    "tiktok": _dibujar_nota_musical,
    "whatsapp": _dibujar_burbuja_chat,
}


@functools.cache
def _icono_bytes(clave: str) -> bytes:
    """Render a small circular gray badge icon in-memory — no external icon
    assets, no brand colors (the identidad's own logo is the priority visual
    element; these are neutral, gray, secondary marks). Drawn at 4x scale and
    downsampled for anti-aliased edges, cached since the same handful of
    icons is reused on every informe generated."""
    from PIL import Image as PILImage
    from PIL import ImageDraw

    lado = _ICONO_LADO_PX
    imagen = PILImage.new("RGBA", (lado, lado), (0, 0, 0, 0))
    draw = ImageDraw.Draw(imagen)
    draw.ellipse((0, 0, lado - 1, lado - 1), fill=_ICONO_COLOR_FONDO)
    _DIBUJANTES[clave](draw, lado)
    imagen = imagen.resize(
        (_ICONO_LADO_FINAL_PX, _ICONO_LADO_FINAL_PX), PILImage.Resampling.LANCZOS
    )
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


class LinkedImage(Image):  # type: ignore[misc]  # reportlab ships no type stubs
    """An `Image` flowable that opens `href` when clicked in the rendered PDF.

    `reportlab.platypus.Paragraph`'s `<link>` tag only wraps text/inline
    content — an `Image` flowable placed in a `Table` cell needs its own
    clickable region, added via `canvas.linkURL` after the image itself is
    drawn. `relative=1` keeps the rect in the flowable's own coordinate
    space, so it doesn't matter where this ends up laid out on the page.
    """

    def __init__(self, fileobj: object, href: str, **kwargs: object) -> None:
        super().__init__(fileobj, **kwargs)
        self._href = href

    def draw(self) -> None:
        super().draw()
        self.canv.linkURL(self._href, (0, 0, self.drawWidth, self.drawHeight), relative=1)


def _icono_link(clave: str, href: str, lado: float = 0.42 * cm) -> LinkedImage:
    return LinkedImage(io.BytesIO(_icono_bytes(clave)), href, width=lado, height=lado)


def _fila_icono_texto(icono: Flowable, texto: Paragraph, ancho_icono: float) -> Table:
    """A tight [icon][text] pair, e.g. the WhatsApp badge next to the phone number."""
    tabla = Table([[icono, texto]], colWidths=[ancho_icono, None])
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 4),
                ("RIGHTPADDING", (1, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tabla


def _fila_iconos(iconos: list[Flowable]) -> Table:
    """A horizontal row of icon badges — Sitio web / Instagram / Facebook / TikTok."""
    tabla = Table([iconos], colWidths=[None] * len(iconos))
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tabla


class _Styles:
    """Small bundle of `ParagraphStyle`s reused across every section builder."""

    def __init__(self) -> None:
        base = getSampleStyleSheet()
        self.normal = base["Normal"]
        self.nombre_comercial = ParagraphStyle(
            "nombre_comercial", parent=base["Heading2"], fontSize=15, spaceAfter=2
        )
        self.contacto = ParagraphStyle(
            "contacto", parent=base["Normal"], fontSize=8.5, textColor=_COLOR_GRIS, leading=11
        )
        self.titulo_informe = ParagraphStyle(
            "titulo_informe",
            parent=base["Heading1"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=10,
        )
        self.subtitulo = ParagraphStyle(
            "subtitulo", parent=base["Heading3"], fontSize=11.5, spaceBefore=4, spaceAfter=6
        )
        self.celda = ParagraphStyle("celda", parent=base["Normal"], fontSize=9, leading=12)
        self.celda_tabla = ParagraphStyle(
            "celda_tabla", parent=base["Normal"], fontSize=8, leading=10
        )
        self.cierre_titulo = ParagraphStyle(
            "cierre_titulo",
            parent=base["Heading2"],
            fontSize=13,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=8,
        )
        self.credito_sistema = ParagraphStyle(
            "credito_sistema",
            parent=base["Normal"],
            fontSize=7.5,
            textColor=_COLOR_GRIS,
            alignment=TA_CENTER,
            spaceBefore=10,
        )


def _imagen_logo(logo_bytes: bytes, lado_max: float = 2.4 * cm) -> Image | None:
    try:
        from PIL import Image as PILImage

        with PILImage.open(io.BytesIO(logo_bytes)) as imagen:
            ancho_px, alto_px = imagen.size
    except Exception:
        return None
    if not ancho_px or not alto_px:
        return None
    escala = min(lado_max / ancho_px, lado_max / alto_px)
    return Image(io.BytesIO(logo_bytes), width=ancho_px * escala, height=alto_px * escala)


def _lineas_contacto(identidad: IdentidadComercial | None, styles: _Styles) -> list[Flowable]:
    """Build the identidad's contact/social block.

    Social values (sitio web, Instagram, Facebook, TikTok) render as small
    gray icon badges, clickable, no visible URL/label — the logo is the one
    branded visual, everything else stays neutral (see `_ICONO_COLOR_FONDO`).
    Teléfono keeps showing as readable text (it's information on its own,
    not just a link) with a WhatsApp badge as its click target. Email stays
    plain clickable text — no widely-recognized neutral "envelope" glyph
    was worth adding for one field.
    """
    if identidad is None:
        return []
    lineas: list[Flowable] = []
    if identidad.razon_social:
        lineas.append(Paragraph(_escape(identidad.razon_social), styles.contacto))
    if identidad.nit:
        lineas.append(Paragraph(f"NIT {_escape(identidad.nit)}", styles.contacto))

    if identidad.telefono:
        icono = _icono_link("whatsapp", _href_whatsapp(identidad.telefono))
        texto = Paragraph(_escape(identidad.telefono), styles.contacto)
        lineas.append(_fila_icono_texto(icono, texto, icono.drawWidth))
    if identidad.email:
        lineas.append(
            Paragraph(_link_texto(f"mailto:{identidad.email}", identidad.email), styles.contacto)
        )

    iconos_redes: list[Flowable] = []
    if identidad.sitio_web:
        iconos_redes.append(_icono_link("web", _href_sitio_web(identidad.sitio_web)))
    if identidad.instagram:
        iconos_redes.append(
            _icono_link("instagram", _href_red_social(identidad.instagram, "instagram.com"))
        )
    if identidad.facebook:
        iconos_redes.append(
            _icono_link("facebook", _href_red_social(identidad.facebook, "facebook.com"))
        )
    texto_otras_redes: list[str] = []
    if identidad.otras_redes:
        for label, valor in _partes_otras_redes(identidad.otras_redes):
            if _es_tiktok(label, valor):
                iconos_redes.append(_icono_link("tiktok", valor))
        texto_otras_redes = _lineas_otras_redes_sin_iconos(identidad.otras_redes)
    if iconos_redes:
        lineas.append(_fila_iconos(iconos_redes))
    if texto_otras_redes:
        lineas.append(Paragraph(" · ".join(texto_otras_redes), styles.contacto))

    return lineas


def _bloque_identidad(
    identidad: IdentidadComercial | None, logo_bytes: bytes | None, styles: _Styles
) -> list[Flowable]:
    nombre = identidad.nombre_comercial if identidad else "Portal Vallenato"
    columna_texto: list[Flowable] = [
        Paragraph(f"<b>{_escape(nombre)}</b>", styles.nombre_comercial)
    ]
    columna_texto.extend(_lineas_contacto(identidad, styles))

    logo = _imagen_logo(logo_bytes) if logo_bytes else None
    if logo is not None:
        tabla = Table([[logo, columna_texto]], colWidths=[3 * cm, None])
    else:
        tabla = Table([[columna_texto]], colWidths=[None])
    tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [tabla]


def _fila_resumen(label: str, valor: str, styles: _Styles) -> list[Paragraph]:
    return [
        Paragraph(f"<b>{_escape(label)}</b>", styles.celda),
        Paragraph(valor, styles.celda),
    ]


def _tabla_resumen(filas: list[list[Paragraph]]) -> Table:
    tabla = Table(filas, colWidths=[6.2 * cm, 9.8 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, _COLOR_BORDE),
            ]
        )
    )
    return tabla


def _seccion_resumen_ejecutivo(reporte: ReportePauta, styles: _Styles) -> list[Flowable]:
    pauta = reporte.pauta
    filas = [
        _fila_resumen("Cliente", _escape(reporte.cliente_nombre or "—"), styles),
        _fila_resumen(
            "Periodo contratado",
            f"{_fmt_fecha(pauta.fecha_inicio)} – {_fmt_fecha(pauta.fecha_fin)}",
            styles,
        ),
        _fila_resumen("Valor contratado", _fmt_moneda(pauta.valor_pagado), styles),
        _fila_resumen("Publicaciones contratadas", str(pauta.publicaciones_contratadas), styles),
        _fila_resumen("Publicaciones realizadas", str(reporte.publicaciones_consumidas), styles),
        _fila_resumen("Publicaciones restantes", str(reporte.publicaciones_restantes), styles),
        _fila_resumen(
            "Canales utilizados",
            ", ".join(_CANAL_LABELS[c] for c in reporte.canales_utilizados) or "—",
            styles,
        ),
        _fila_resumen("Total de publicaciones incluidas", str(len(reporte.solicitudes)), styles),
    ]
    if reporte.fecha_primera_publicacion is not None:
        filas.append(
            _fila_resumen(
                "Fecha de primera publicación",
                _fmt_fecha_negocio(reporte.fecha_primera_publicacion),
                styles,
            )
        )
    if reporte.fecha_ultima_publicacion is not None:
        filas.append(
            _fila_resumen(
                "Fecha de última publicación",
                _fmt_fecha_negocio(reporte.fecha_ultima_publicacion),
                styles,
            )
        )
    return [
        Paragraph("Resumen de campaña", styles.subtitulo),
        _tabla_resumen(filas),
    ]


def _seccion_contrato(reporte: ReportePauta, styles: _Styles) -> list[Flowable]:
    pauta = reporte.pauta
    estado = "Vigente" if reporte.vigente else "Vencido"
    if reporte.cuota_agotada:
        estado += " · Cupo agotado"
    filas = [
        _fila_resumen("Fecha de inicio", _fmt_fecha(pauta.fecha_inicio), styles),
        _fila_resumen("Fecha de finalización", _fmt_fecha(pauta.fecha_fin), styles),
        _fila_resumen("Valor contratado", _fmt_moneda(pauta.valor_pagado), styles),
        _fila_resumen("Tipo de plan", _PAUTA_TIPO_LABELS[pauta.tipo], styles),
        _fila_resumen("Publicaciones contratadas", str(pauta.publicaciones_contratadas), styles),
        _fila_resumen("Publicaciones consumidas", str(reporte.publicaciones_consumidas), styles),
        _fila_resumen("Estado final del contrato", estado, styles),
    ]
    return [
        Paragraph(f"Cliente: {_escape(reporte.cliente_nombre or '—')}", styles.subtitulo),
        Paragraph("Pauta / Contrato", styles.subtitulo),
        _tabla_resumen(filas),
    ]


def _enlace_canal(
    solicitud: ReporteSolicitud, canal: CanalPublicacion, styles: _Styles
) -> Paragraph:
    for destino in solicitud.destinos:
        if destino.canal == canal:
            return Paragraph(_enlace_o_guion(destino.enlace), styles.celda_tabla)
    return Paragraph("—", styles.celda_tabla)


def _seccion_detalle_publicaciones(reporte: ReportePauta, styles: _Styles) -> list[Flowable]:
    encabezado: list[Flowable | str] = [
        Paragraph("<b>Fecha</b>", styles.celda_tabla),
        Paragraph("<b>Publicación</b>", styles.celda_tabla),
        Paragraph("<b>Página web</b>", styles.celda_tabla),
        Paragraph("<b>Facebook</b>", styles.celda_tabla),
        Paragraph("<b>Instagram</b>", styles.celda_tabla),
    ]
    filas: list[list[Flowable | str]] = [encabezado]

    if not reporte.solicitudes:
        filas.append(
            [
                Paragraph(
                    "Este contrato aún no tiene publicaciones consumidas registradas.",
                    styles.celda_tabla,
                ),
                "",
                "",
                "",
                "",
            ]
        )
    else:
        for solicitud in reporte.solicitudes:
            fecha_ref = solicitud.fecha_cierre or solicitud.fecha_recepcion
            titulo = _titulo_o_fragmento(solicitud)
            filas.append(
                [
                    Paragraph(_fmt_fecha_negocio(fecha_ref), styles.celda_tabla),
                    Paragraph(titulo, styles.celda_tabla),
                    _enlace_canal(solicitud, CanalPublicacion.WORDPRESS, styles),
                    _enlace_canal(solicitud, CanalPublicacion.FACEBOOK, styles),
                    _enlace_canal(solicitud, CanalPublicacion.INSTAGRAM, styles),
                ]
            )

    tabla = Table(filas, colWidths=[2.2 * cm, 5 * cm, 2.9 * cm, 2.9 * cm, 2.9 * cm], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _COLOR_FONDO_ENCABEZADO),
                ("GRID", (0, 0), (-1, -1), 0.25, _COLOR_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [Paragraph("Detalle de publicaciones", styles.subtitulo), tabla]


def _seccion_cierre(
    identidad: IdentidadComercial | None, logo_bytes: bytes | None, styles: _Styles
) -> list[Flowable]:
    nombre = identidad.nombre_comercial if identidad else "Portal Vallenato"
    elementos: list[Flowable] = [
        Spacer(1, 0.4 * cm),
        HRFlowable(width="100%", color=_COLOR_BORDE, thickness=0.75),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Gracias por confiar en <b>{_escape(nombre)}</b>", styles.cierre_titulo),
    ]
    elementos.extend(_bloque_identidad(identidad, logo_bytes, styles))
    elementos.append(Paragraph(f"Generado con {_escape(_NOMBRE_SISTEMA)}", styles.credito_sistema))
    return elementos


def generar_informe_pauta_pdf(
    reporte: ReportePauta,
    identidad: IdentidadComercial | None,
    logo_bytes: bytes | None,
) -> bytes:
    """Render `reporte` as a PDF (bytes) — the "Generar informe PDF" download.

    Never touches a repository, a `UnitOfWork`, or the network — every
    input is already resolved by the caller (`GET /pautas/{id}/informe.pdf`
    in `app.api.routers.pautas`), same "handed its data, doesn't fetch it"
    discipline `core.services.reporte_service` follows one layer down.
    """
    styles = _Styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Informe de resultados de campaña",
    )

    story: list[Flowable] = []
    story.extend(_bloque_identidad(identidad, logo_bytes, styles))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", color=_COLOR_BORDE, thickness=0.75))
    story.append(Paragraph("INFORME DE RESULTADOS DE CAMPAÑA", styles.titulo_informe))

    story.extend(_seccion_resumen_ejecutivo(reporte, styles))
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_seccion_contrato(reporte, styles))
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_seccion_detalle_publicaciones(reporte, styles))

    story.extend(_seccion_cierre(identidad, logo_bytes, styles))

    doc.build(story)
    return buffer.getvalue()
