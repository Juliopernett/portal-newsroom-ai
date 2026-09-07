"""Renders a Pauta's contract terms as a client-facing PDF.

The "Contrato" download / "Enviar contrato al cliente" share link — the
document sent to the client *when the pauta is about to start*, before
there is anything to report on. Deliberately the same layout language as
`app.api.pdf_informe` (identidad header, plain facts tables, cierre),
just without the results half: no "publicaciones realizadas/restantes",
no detalle de publicaciones, no cupo — only who contracted and what.
Cliente-facing, so it carries the client's own data (nombre, tipo,
contacto, Instagram) but never internal notes.

Same discipline as `pdf_informe`: this module only *renders* data already
resolved by the caller (`GET /pautas/{id}/contrato.pdf` in
`app.api.routers.pautas`). It never touches a repository, recomputes
`tipo`, or reaches the network. All the small formatting/identidad
helpers are shared from `pdf_informe` so the two documents can never
drift in how a date, a monto, or the identidad block looks.

Unlike the informe, the contrato's cierre does *not* repeat the logo /
razón social / redes: this is a one-page document and that block is
already in the header a few centímetros above — printing it twice just
looked cramped (user feedback, 2026-09-07). Only the "gracias" line and
the system credit stay.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.api.pdf_informe import (
    _COLOR_BORDE,
    _NOMBRE_SISTEMA,
    _PAUTA_TIPO_LABELS,
    _bloque_identidad,
    _escape,
    _fila_resumen,
    _fmt_fecha,
    _fmt_moneda,
    _href_red_social,
    _link_texto,
    _Styles,
    _tabla_resumen,
)
from core.entities.client import Client, ClientType
from core.entities.identidad_comercial import IdentidadComercial
from core.entities.pauta import Pauta

_CLIENT_TIPO_LABELS = {
    ClientType.ARTISTA: "Artista",
    ClientType.MANAGER: "Mánager",
    ClientType.PROMOTOR: "Promotor",
    ClientType.EMPRESARIO: "Empresario",
}


def _seccion_datos_cliente(cliente: Client | None, styles: _Styles) -> list[Flowable]:
    if cliente is None:
        filas = [_fila_resumen("Nombre", "—", styles)]
    else:
        filas = [
            _fila_resumen("Nombre", _escape(cliente.nombre), styles),
            _fila_resumen("Tipo", _CLIENT_TIPO_LABELS[cliente.tipo], styles),
            _fila_resumen("Teléfono", _escape(cliente.telefono), styles),
        ]
        if cliente.instagram and cliente.instagram.strip():
            handle = cliente.instagram.strip()
            filas.append(
                _fila_resumen(
                    "Instagram",
                    _link_texto(_href_red_social(handle, "instagram.com"), handle),
                    styles,
                )
            )
    return [
        Paragraph("Datos del cliente", styles.subtitulo),
        _tabla_resumen(filas),
    ]


def _seccion_datos_contrato(pauta: Pauta, styles: _Styles) -> list[Flowable]:
    filas = [
        _fila_resumen("Tipo de plan", _PAUTA_TIPO_LABELS[pauta.tipo], styles),
        _fila_resumen("Fecha de inicio", _fmt_fecha(pauta.fecha_inicio), styles),
        _fila_resumen("Fecha de finalización", _fmt_fecha(pauta.fecha_fin), styles),
        _fila_resumen("Publicaciones contratadas", str(pauta.publicaciones_contratadas), styles),
        _fila_resumen("Valor del contrato", _fmt_moneda(pauta.valor_pagado), styles),
    ]
    if pauta.saldo_pendiente > 0:
        filas.append(
            _fila_resumen("Saldo pendiente de pago", _fmt_moneda(pauta.saldo_pendiente), styles)
        )
    if pauta.observaciones and pauta.observaciones.strip():
        filas.append(_fila_resumen("Observaciones", _escape(pauta.observaciones.strip()), styles))
    return [
        Paragraph("Datos del contrato", styles.subtitulo),
        _tabla_resumen(filas),
    ]


def _seccion_cierre_contrato(nombre_comercial: str, styles: _Styles) -> list[Flowable]:
    """A minimal cierre — no repeated identidad block (see module docstring)."""
    return [
        Spacer(1, 0.6 * cm),
        HRFlowable(width="100%", color=_COLOR_BORDE, thickness=0.75),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"Gracias por confiar en <b>{_escape(nombre_comercial)}</b>",
            styles.cierre_titulo,
        ),
        Paragraph(f"Generado con {_escape(_NOMBRE_SISTEMA)}", styles.credito_sistema),
    ]


def generar_contrato_pauta_pdf(
    pauta: Pauta,
    cliente: Client | None,
    identidad: IdentidadComercial | None,
    logo_bytes: bytes | None,
) -> bytes:
    """Render `pauta`'s contract terms as a PDF (bytes) — the "Contrato" download.

    Never touches a repository, a `UnitOfWork`, or the network — every
    input is already resolved by the caller, the same "handed its data,
    doesn't fetch it" discipline `pdf_informe.generar_informe_pauta_pdf`
    follows.
    """
    styles = _Styles()
    nombre_comercial = identidad.nombre_comercial if identidad else "Portal Vallenato"
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Detalle del contrato",
    )

    story: list[Flowable] = []
    story.extend(_bloque_identidad(identidad, logo_bytes, styles))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", color=_COLOR_BORDE, thickness=0.75))
    story.append(Paragraph("CONTRATO DE PUBLICIDAD", styles.titulo_informe))

    story.append(
        Paragraph(
            "A continuación se detallan los términos de la pauta publicitaria "
            f"contratada con <b>{_escape(nombre_comercial)}</b>.",
            styles.celda,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_seccion_datos_cliente(cliente, styles))
    story.append(Spacer(1, 0.4 * cm))

    story.extend(_seccion_datos_contrato(pauta, styles))

    story.extend(_seccion_cierre_contrato(nombre_comercial, styles))

    doc.build(story)
    return buffer.getvalue()
