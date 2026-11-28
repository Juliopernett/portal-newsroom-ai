"""Excel (.xlsx) rendering of the Reportes tab.

Presentation only, like `app.api.pdf_informe`: the router decides which rows
each report has, this module turns them into a workbook with real dates and
numbers (so they can be summed and sorted), a frozen and filterable header and
a totals row.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


class Formato(StrEnum):
    TEXTO = "texto"
    FECHA = "fecha"
    MES = "mes"
    ENTERO = "entero"
    PESOS = "pesos"
    DOLARES = "dolares"


_FORMATOS_NUMERICOS = {
    Formato.FECHA: "dd/mm/yyyy",
    Formato.MES: "mmm yyyy",
    Formato.ENTERO: "#,##0",
    Formato.PESOS: '"$" #,##0;[Red]-"$" #,##0',
    Formato.DOLARES: '"US$" #,##0.00',
}

_ANCHO_MINIMO = {
    Formato.TEXTO: 14,
    Formato.FECHA: 13,
    Formato.MES: 12,
    Formato.ENTERO: 12,
    Formato.PESOS: 18,
    Formato.DOLARES: 16,
}
_ANCHO_MAXIMO = 60


@dataclass(frozen=True, slots=True)
class Columna:
    titulo: str
    formato: Formato = Formato.TEXTO
    totalizar: bool = False


@dataclass(frozen=True, slots=True)
class Hoja:
    nombre: str
    columnas: Sequence[Columna]
    filas: Sequence[Sequence[object]]


def construir_excel(hojas: Sequence[Hoja], color_encabezado: str) -> bytes:
    """Return the `.xlsx` bytes of a workbook with one sheet per `Hoja`.

    `color_encabezado` is `#RRGGBB`; the header lettering on it is white.
    """
    libro = Workbook()
    libro.remove(libro.active)
    for hoja in hojas:
        _escribir_hoja(libro.create_sheet(hoja.nombre), hoja, color_encabezado.lstrip("#"))
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _escribir_hoja(ws: Worksheet, hoja: Hoja, color: str) -> None:
    for indice, columna in enumerate(hoja.columnas, start=1):
        celda = ws.cell(row=1, column=indice, value=columna.titulo)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=color)
        celda.alignment = Alignment(vertical="center", wrap_text=True)

    for numero, fila in enumerate(hoja.filas, start=2):
        for indice, (columna, valor) in enumerate(zip(hoja.columnas, fila, strict=True), start=1):
            _escribir_celda(ws, numero, indice, columna.formato, valor)

    ultima_fila = len(hoja.filas) + 1
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(hoja.columnas))}{ultima_fila}"
    if hoja.filas and any(columna.totalizar for columna in hoja.columnas):
        _escribir_totales(ws, hoja, ultima_fila)
    _ajustar_anchos(ws, hoja)

    # Printing: one page wide, header repeated on every page.
    ws.print_title_rows = "1:1"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _escribir_celda(
    ws: Worksheet, fila: int, columna: int, formato: Formato, valor: object
) -> None:
    celda = ws.cell(row=fila, column=columna)
    if isinstance(valor, str):
        celda.value = ILLEGAL_CHARACTERS_RE.sub("", valor)
        # Typed-in text must stay text: a description starting with "=" would
        # otherwise run as a formula when the file is opened.
        celda.data_type = "s"
        celda.alignment = Alignment(vertical="top", wrap_text=True)
        return
    celda.value = valor
    celda.alignment = Alignment(vertical="top")
    if formato in _FORMATOS_NUMERICOS:
        celda.number_format = _FORMATOS_NUMERICOS[formato]


def _escribir_totales(ws: Worksheet, hoja: Hoja, ultima_fila: int) -> None:
    fila_total = ultima_fila + 1
    borde = Border(top=Side(style="medium"))
    for indice, columna in enumerate(hoja.columnas, start=1):
        celda = ws.cell(row=fila_total, column=indice)
        celda.font = Font(bold=True)
        celda.border = borde
        if indice == 1:
            celda.value = "TOTAL"
        if columna.totalizar:
            letra = get_column_letter(indice)
            # SUBTOTAL 109 = sum of the visible rows, so the total follows the filters.
            celda.value = f"=SUBTOTAL(109,{letra}2:{letra}{ultima_fila})"
            celda.number_format = _FORMATOS_NUMERICOS[columna.formato]


def _ajustar_anchos(ws: Worksheet, hoja: Hoja) -> None:
    for indice, columna in enumerate(hoja.columnas):
        largo = len(columna.titulo) + 4  # room for the filter arrow
        if columna.formato is Formato.TEXTO:
            for fila in hoja.filas:
                valor = fila[indice]
                if not isinstance(valor, date) and valor is not None:
                    largo = max(largo, len(str(valor)) + 2)
        ancho = min(max(largo, _ANCHO_MINIMO[columna.formato]), _ANCHO_MAXIMO)
        ws.column_dimensions[get_column_letter(indice + 1)].width = ancho
