"""Unit tests for app.api.pdf_informe's pure text-formatting helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.api.pdf_informe import (
    _href_red_social,
    _href_sitio_web,
    _href_telefono,
    _lineas_contacto,
    _lineas_otras_redes,
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


def test_href_telefono_conserva_digitos_y_signo_mas() -> None:
    assert _href_telefono("+57 315 095 4255") == "tel:+573150954255"


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


def test_lineas_otras_redes_linkea_solo_cuando_el_valor_es_una_url() -> None:
    piezas = _lineas_otras_redes("TikTok: https://www.tiktok.com/@portalvallenato")

    assert len(piezas) == 1
    assert "<link" in piezas[0]
    assert ">TikTok<" in piezas[0]
    assert ">https://www.tiktok.com/@portalvallenato<" not in piezas[0]


def test_lineas_otras_redes_deja_texto_libre_sin_url_intacto() -> None:
    piezas = _lineas_otras_redes("Nos escuchan en toda Colombia")

    assert piezas == ["Nos escuchan en toda Colombia"]


def test_lineas_contacto_muestra_nombres_no_urls_crudas() -> None:
    identidad = IdentidadComercial(
        nombre_comercial="Portal Vallenato",
        telefono="+573150954255",
        email="contacto@portalvallenato.com",
        sitio_web="https://www.portalvallenato.com/",
        instagram="https://www.instagram.com/portalvallenatoelite",
        facebook="https://www.facebook.com/VallenatoPortal",
        otras_redes="TikTok: https://www.tiktok.com/@portalvallenato",
    )

    lineas = "\n".join(_lineas_contacto(identidad))

    def visible_texto(url: str) -> str:
        # La URL cruda solo debe aparecer dentro de href="..." (para que el
        # link funcione) — nunca como el texto visible entre `>` y `</font>`.
        return f">{url}<"

    assert "Sitio web" in lineas
    assert visible_texto("https://www.portalvallenato.com/") not in lineas
    assert "Instagram" in lineas
    assert visible_texto("https://www.instagram.com/portalvallenatoelite") not in lineas
    assert "Facebook" in lineas
    assert visible_texto("https://www.facebook.com/VallenatoPortal") not in lineas
    assert "TikTok" in lineas
    assert visible_texto("https://www.tiktok.com/@portalvallenato") not in lineas
    # El teléfono y el correo sí se muestran tal cual — ya son su propia etiqueta legible.
    assert ">+573150954255<" in lineas
    assert ">contacto@portalvallenato.com<" in lineas
