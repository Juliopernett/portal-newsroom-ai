"""Unit tests for app.api.pdf_contrato — the contract-terms PDF.

The rendering itself is exercised end-to-end in
`tests/integration/api/test_contrato_pauta_api.py`; here we check the
section builders that have real branching (cliente sin Instagram, saldo
pendiente / observaciones shown only when present) and that the whole
document builds to a well-formed file.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from reportlab.platypus import Paragraph

from app.api.pdf_contrato import (
    _seccion_datos_cliente,
    _seccion_datos_contrato,
    generar_contrato_pauta_pdf,
)
from app.api.pdf_informe import _Styles
from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta


def _pauta(**overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": "client-1",
        "fecha_inicio": date(2026, 9, 10),
        "fecha_fin": date(2026, 10, 10),
        "publicaciones_contratadas": 8,
        "valor_pagado": Decimal("280000"),
        "fecha_pago": date(2026, 9, 10),
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def _cliente(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def _filas_texto(seccion: list) -> str:
    """Flatten every Paragraph across the section, table cells included."""
    partes: list[str] = []
    for flowable in seccion:
        if isinstance(flowable, Paragraph):
            partes.append(flowable.text)
        else:  # the _tabla_resumen Table
            for fila in getattr(flowable, "_cellvalues", []):
                for celda in fila:
                    if isinstance(celda, Paragraph):
                        partes.append(celda.text)
    return " ".join(partes)


def test_datos_cliente_incluye_nombre_tipo_y_telefono() -> None:
    texto = _filas_texto(_seccion_datos_cliente(_cliente(), _Styles()))

    assert "Silvestre Dangond" in texto
    assert "Artista" in texto
    assert "+573001112233" in texto


def test_datos_cliente_muestra_instagram_como_enlace_solo_cuando_existe() -> None:
    sin_ig = _filas_texto(_seccion_datos_cliente(_cliente(instagram=None), _Styles()))
    con_ig = _filas_texto(
        _seccion_datos_cliente(_cliente(instagram="@silvestrofficial"), _Styles())
    )

    assert "Instagram" not in sin_ig
    assert "Instagram" in con_ig
    assert "@silvestrofficial" in con_ig
    assert "instagram.com/silvestrofficial" in con_ig


def test_datos_cliente_sin_cliente_no_rompe() -> None:
    assert "—" in _filas_texto(_seccion_datos_cliente(None, _Styles()))


def test_datos_contrato_incluye_los_campos_base() -> None:
    texto = _filas_texto(_seccion_datos_contrato(_pauta(), _Styles()))

    assert "Publicaciones contratadas" in texto
    assert "$280.000" in texto


def test_datos_contrato_omite_saldo_cuando_esta_en_cero() -> None:
    seccion = _seccion_datos_contrato(_pauta(saldo_pendiente=Decimal("0")), _Styles())

    assert "Saldo pendiente" not in _filas_texto(seccion)


def test_datos_contrato_muestra_saldo_pendiente_cuando_lo_hay() -> None:
    seccion = _seccion_datos_contrato(_pauta(saldo_pendiente=Decimal("120000")), _Styles())
    texto = _filas_texto(seccion)

    assert "Saldo pendiente de pago" in texto
    assert "$120.000" in texto


def test_datos_contrato_muestra_observaciones_solo_cuando_existen() -> None:
    sin_obs = _seccion_datos_contrato(_pauta(observaciones=None), _Styles())
    con_obs = _seccion_datos_contrato(
        _pauta(observaciones="Incluye pauta en historia de Instagram"), _Styles()
    )

    assert "Observaciones" not in _filas_texto(sin_obs)
    assert "Incluye pauta en historia de Instagram" in _filas_texto(con_obs)


def test_generar_contrato_pdf_devuelve_un_archivo_pdf_valido() -> None:
    pdf = generar_contrato_pauta_pdf(_pauta(), _cliente(instagram="@silvestrofficial"), None, None)

    assert pdf.startswith(b"%PDF")
