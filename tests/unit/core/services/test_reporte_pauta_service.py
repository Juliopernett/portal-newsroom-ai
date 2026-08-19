"""Unit tests for construir_reporte_pauta — pure, no I/O.

Covers the sprint's explicit test list: a Pauta with no publications, with
one, with several, a solicitud with multiple destinos (must count once),
a destino with no URL, and vigente/vencida contracts — see
`core.services.reporte_service.construir_reporte_pauta`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from core.entities.client import Client, ClientType
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.pauta_service import PautaService
from core.services.reporte_service import construir_reporte_pauta


def _pauta(**overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": "client-1",
        "fecha_inicio": date(2026, 7, 30),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000"),
        "fecha_pago": date(2026, 7, 30),
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def _solicitud(pauta_id: str, **overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "pauta_id": pauta_id,
        "texto": "Anuncio de nueva canción",
        "fecha_cierre": datetime(2026, 8, 6, tzinfo=UTC),
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def _destino(solicitud_id: str, **overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": solicitud_id,
        "canal": CanalPublicacion.WORDPRESS,
        "estado": EstadoDestino.PUBLICADO,
        "fecha_publicacion": datetime(2026, 8, 6, 20, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def _cliente(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def _clock_dentro_de_vigencia() -> date:
    return date(2026, 8, 10)


def _clock_despues_de_vencer() -> date:
    return date(2026, 9, 15)


def test_pauta_sin_publicaciones() -> None:
    pauta = _pauta(id="pauta-1")
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [], [], _cliente(), service)

    assert reporte.publicaciones_consumidas == 0
    assert reporte.publicaciones_restantes == pauta.publicaciones_contratadas
    assert reporte.solicitudes == ()
    assert reporte.canales_utilizados == ()
    assert reporte.fecha_primera_publicacion is None
    assert reporte.fecha_ultima_publicacion is None


def test_pauta_con_una_publicacion() -> None:
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta.id, titulo="Lanzamiento sencillo")
    destino = _destino(solicitud.id, wp_url="https://portalvallenato.com/?p=1")
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [solicitud], [destino], _cliente(), service)

    assert reporte.publicaciones_consumidas == 1
    assert len(reporte.solicitudes) == 1
    assert reporte.solicitudes[0].publication_request_id == solicitud.id
    assert reporte.solicitudes[0].destinos[0].enlace == "https://portalvallenato.com/?p=1"


def test_pauta_con_multiples_publicaciones() -> None:
    pauta = _pauta(id="pauta-1")
    solicitudes = [_solicitud(pauta.id) for _ in range(3)]
    destinos = [_destino(s.id) for s in solicitudes]
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, solicitudes, destinos, _cliente(), service)

    assert reporte.publicaciones_consumidas == 3
    assert len(reporte.solicitudes) == 3


def test_solicitud_con_varios_destinos_cuenta_una_sola_vez() -> None:
    """WordPress + Facebook + Instagram en la misma solicitud sigue siendo 1 consumo."""
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta.id)
    destinos = [
        _destino(
            solicitud.id,
            canal=CanalPublicacion.WORDPRESS,
            wp_url="https://portalvallenato.com/?p=1",
        ),
        _destino(
            solicitud.id,
            canal=CanalPublicacion.FACEBOOK,
            url_publicacion="https://facebook.com/portalvallenato/posts/1",
        ),
        _destino(
            solicitud.id,
            canal=CanalPublicacion.INSTAGRAM,
            url_publicacion="https://instagram.com/p/abc",
        ),
    ]
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [solicitud], destinos, _cliente(), service)

    assert reporte.publicaciones_consumidas == 1
    assert len(reporte.solicitudes) == 1
    assert set(reporte.canales_utilizados) == {
        CanalPublicacion.WORDPRESS,
        CanalPublicacion.FACEBOOK,
        CanalPublicacion.INSTAGRAM,
    }
    assert len(reporte.solicitudes[0].destinos) == 3


def test_destino_sin_url() -> None:
    """WORDPRESS puede quedar PUBLICADO sin wp_url — el reporte no debe inventar un enlace."""
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta.id)
    destino = _destino(solicitud.id, canal=CanalPublicacion.WORDPRESS, wp_url=None)
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [solicitud], [destino], _cliente(), service)

    assert reporte.publicaciones_consumidas == 1
    assert reporte.solicitudes[0].destinos[0].enlace is None


def test_publicaciones_consumidas_ignora_solicitudes_de_otra_pauta() -> None:
    pauta = _pauta(id="pauta-1")
    otra_pauta = _pauta(id="pauta-2")
    de_esta_pauta = _solicitud(pauta.id)
    de_otra_pauta = _solicitud(otra_pauta.id)
    solicitudes = [de_esta_pauta, de_otra_pauta]
    destinos = [_destino(de_esta_pauta.id), _destino(de_otra_pauta.id)]
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, solicitudes, destinos, _cliente(), service)

    assert reporte.publicaciones_consumidas == 1
    assert len(reporte.solicitudes) == 1
    assert reporte.solicitudes[0].publication_request_id == de_esta_pauta.id


def test_contrato_activo_vigente() -> None:
    pauta = _pauta(id="pauta-1", fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [], [], _cliente(), service)

    assert reporte.vigente is True
    assert reporte.vencida is False


def test_contrato_vencido() -> None:
    pauta = _pauta(id="pauta-1", fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=_clock_despues_de_vencer)

    reporte = construir_reporte_pauta(pauta, [], [], _cliente(), service)

    assert reporte.vigente is False
    assert reporte.vencida is True


def test_contrato_con_publicaciones_historicas_calcula_primera_y_ultima_fecha() -> None:
    pauta = _pauta(id="pauta-1")
    temprana = _solicitud(pauta.id)
    tardia = _solicitud(pauta.id)
    destinos = [
        _destino(temprana.id, fecha_publicacion=datetime(2026, 8, 1, 9, 0, tzinfo=UTC)),
        _destino(tardia.id, fecha_publicacion=datetime(2026, 8, 20, 18, 0, tzinfo=UTC)),
    ]
    service = PautaService(clock=_clock_despues_de_vencer)

    reporte = construir_reporte_pauta(pauta, [temprana, tardia], destinos, _cliente(), service)

    assert reporte.fecha_primera_publicacion == datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    assert reporte.fecha_ultima_publicacion == datetime(2026, 8, 20, 18, 0, tzinfo=UTC)


def test_publicaciones_consumidas_coincide_siempre_con_cantidad_de_solicitudes_reportadas() -> None:
    """Garantía central del sprint: el conteo de PautaService y la lista mostrada
    en el informe nunca pueden divergir — ambos derivan de `esta_completa`."""
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=5)
    completas = [_solicitud(pauta.id) for _ in range(2)]
    pendiente = _solicitud(pauta.id)
    destinos = [_destino(s.id) for s in completas] + [
        _destino(pendiente.id, estado=EstadoDestino.PENDIENTE, fecha_publicacion=None)
    ]
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [*completas, pendiente], destinos, _cliente(), service)

    assert len(reporte.solicitudes) == reporte.publicaciones_consumidas == 2
    assert reporte.publicaciones_restantes == pauta.publicaciones_contratadas - 2


def test_cliente_none_no_rompe_el_reporte() -> None:
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta.id)
    destino = _destino(solicitud.id)
    service = PautaService(clock=_clock_dentro_de_vigencia)

    reporte = construir_reporte_pauta(pauta, [solicitud], [destino], None, service)

    assert reporte.cliente_nombre is None
    assert reporte.publicaciones_consumidas == 1
