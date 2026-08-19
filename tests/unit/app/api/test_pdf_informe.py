"""Unit tests for app.api.pdf_informe's pure text-formatting/icon helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from reportlab.platypus import Table

from app.api.pdf_informe import (
    LinkedImage,
    _es_tiktok,
    _href_red_social,
    _href_sitio_web,
    _href_whatsapp,
    _lineas_contacto,
    _lineas_otras_redes_sin_iconos,
    _Styles,
    _titulo_o_fragmento,
)
from core.entities.destino_publicacion import CanalPublicacion, EstadoDestino
from core.entities.identidad_comercial import IdentidadComercial
from core.services.reporte_service import ReporteDestino, ReporteSolicitud


def _solicitud(titulo: str | None, texto: str) -> ReporteSolicitud:
    return ReporteSolicitud(
        publication_request_id="solicitud-1",
        titulo=titulo,
        texto=texto,
        cliente_nombre=None,
        pauta_id="pauta-1",
        fecha_recepcion=datetime(2026, 8, 6, tzinfo=UTC),
        fecha_cierre=None,
        completa=True,
        pauta_consumida=True,
        destinos=(
            ReporteDestino(
                canal=CanalPublicacion.WORDPRESS,
                estado=EstadoDestino.PUBLICADO,
                enlace=None,
                fecha_publicacion=None,
                ultimo_error=None,
            ),
        ),
    )


def test_usa_el_titulo_cuando_existe() -> None:
    solicitud = _solicitud(
        titulo="Lanzamiento de sencillo", texto="Contenido largo de la solicitud"
    )

    assert _titulo_o_fragmento(solicitud) == "Lanzamiento de sencillo"


def test_usa_fragmento_del_texto_cuando_no_hay_titulo() -> None:
    solicitud = _solicitud(titulo=None, texto="Este es el contenido completo de la publicación")

    resultado = _titulo_o_fragmento(solicitud)

    assert resultado != ""
    assert resultado.startswith("Este es el contenido completo")


def test_fragmento_corto_no_se_trunca() -> None:
    solicitud = _solicitud(titulo=None, texto="Texto corto")

    assert _titulo_o_fragmento(solicitud) == "Texto corto"


def test_fragmento_largo_se_trunca_con_elipsis() -> None:
    texto_largo = "A" * 200
    solicitud = _solicitud(titulo=None, texto=texto_largo)

    resultado = _titulo_o_fragmento(solicitud, max_len=60)

    assert resultado.endswith("…")
    assert len(resultado) == 61  # 60 chars + el carácter de elipsis


def test_nunca_queda_vacio_ni_con_titulo_ni_con_texto_con_espacios() -> None:
    solicitud = _solicitud(titulo=None, texto="   Texto con espacios al inicio   ")

    resultado = _titulo_o_fragmento(solicitud)

    assert resultado.strip() != ""
    assert resultado.startswith("Texto con espacios")


def test_href_whatsapp_usa_solo_digitos_sin_signo_mas() -> None:
    assert _href_whatsapp("+57 315 095 4255") == "https://wa.me/573150954255"


def test_href_sitio_web_agrega_esquema_si_falta() -> None:
    assert _href_sitio_web("www.portalvallenato.com") == "https://www.portalvallenato.com"


def test_href_sitio_web_respeta_url_absoluta() -> None:
    assert _href_sitio_web("https://portalvallenato.com/") == "https://portalvallenato.com/"


def test_href_red_social_normaliza_handle_a_url_completa() -> None:
    assert _href_red_social("@portalvallenatoelite", "instagram.com") == (
        "https://instagram.com/portalvallenatoelite"
    )


def test_href_red_social_respeta_url_absoluta() -> None:
    url = "https://www.instagram.com/portalvallenatoelite"
    assert _href_red_social(url, "instagram.com") == url


def test_es_tiktok_reconoce_label_tiktok_con_url() -> None:
    assert _es_tiktok("TikTok", "https://www.tiktok.com/@x") is True


def test_es_tiktok_falso_sin_url() -> None:
    assert _es_tiktok("TikTok", "@x") is False


def test_es_tiktok_falso_para_otra_plataforma() -> None:
    assert _es_tiktok("YouTube", "https://youtube.com/@x") is False


def test_lineas_otras_redes_sin_iconos_omite_tiktok() -> None:
    """TikTok se convierte en un ícono aparte (ver `_lineas_contacto`) — no debe
    duplicarse también como línea de texto."""
    piezas = _lineas_otras_redes_sin_iconos("TikTok: https://www.tiktok.com/@portalvallenato")

    assert piezas == []


def test_lineas_otras_redes_sin_iconos_linkea_otra_plataforma_con_url() -> None:
    piezas = _lineas_otras_redes_sin_iconos("YouTube: https://youtube.com/@portalvallenato")

    assert len(piezas) == 1
    assert "<link" in piezas[0]
    assert ">YouTube<" in piezas[0]
    assert ">https://youtube.com/@portalvallenato<" not in piezas[0]


def test_lineas_otras_redes_sin_iconos_deja_texto_libre_intacto() -> None:
    piezas = _lineas_otras_redes_sin_iconos("Nos escuchan en toda Colombia")

    assert piezas == ["Nos escuchan en toda Colombia"]


def _fila_de_iconos(lineas: list) -> Table:
    filas = [
        flowable
        for flowable in lineas
        if isinstance(flowable, Table)
        and all(isinstance(celda, LinkedImage) for celda in flowable._cellvalues[0])
    ]
    assert len(filas) == 1, "se esperaba exactamente una fila de íconos de redes"
    return filas[0]


def test_lineas_contacto_arma_un_icono_gris_por_cada_red_configurada() -> None:
    identidad = IdentidadComercial(
        nombre_comercial="Portal Vallenato",
        telefono="+573150954255",
        email="contacto@portalvallenato.com",
        sitio_web="https://www.portalvallenato.com/",
        instagram="https://www.instagram.com/portalvallenatoelite",
        facebook="https://www.facebook.com/VallenatoPortal",
        otras_redes="TikTok: https://www.tiktok.com/@portalvallenato",
    )

    lineas = _lineas_contacto(identidad, _Styles())

    fila_iconos = _fila_de_iconos(lineas)
    hrefs = {celda._href for celda in fila_iconos._cellvalues[0]}
    assert hrefs == {
        "https://www.portalvallenato.com/",
        "https://www.instagram.com/portalvallenatoelite",
        "https://www.facebook.com/VallenatoPortal",
        "https://www.tiktok.com/@portalvallenato",
    }


def test_lineas_contacto_telefono_muestra_numero_con_icono_whatsapp() -> None:
    identidad = IdentidadComercial(nombre_comercial="Portal Vallenato", telefono="+573150954255")

    lineas = _lineas_contacto(identidad, _Styles())

    filas_con_icono = [
        f
        for f in lineas
        if isinstance(f, Table) and any(isinstance(c, LinkedImage) for c in f._cellvalues[0])
    ]
    assert len(filas_con_icono) == 1
    icono, _texto = filas_con_icono[0]._cellvalues[0]
    assert isinstance(icono, LinkedImage)
    assert icono._href == "https://wa.me/573150954255"


def test_lineas_contacto_sin_identidad_no_rompe() -> None:
    assert _lineas_contacto(None, _Styles()) == []


def test_lineas_contacto_sin_redes_no_agrega_fila_de_iconos() -> None:
    identidad = IdentidadComercial(nombre_comercial="Portal Vallenato")

    lineas = _lineas_contacto(identidad, _Styles())

    assert not any(
        isinstance(f, Table) and any(isinstance(c, LinkedImage) for c in f._cellvalues[0])
        for f in lineas
    )
