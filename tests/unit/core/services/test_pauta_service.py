"""Unit tests for PautaService, using in-memory Pauta/PublicationRequest/DestinoPublicacion data."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.pauta_service import PautaService


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


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "pauta_id": "pauta-1",
        "texto": "Solicitud de ejemplo",
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def _destino_publicado(solicitud: PublicationRequest, **overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": solicitud.id,
        "canal": CanalPublicacion.WORDPRESS,
        "estado": EstadoDestino.PUBLICADO,
        "fecha_publicacion": datetime(2026, 8, 6, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_publicaciones_consumidas_counts_only_complete_requests_of_this_pauta() -> None:
    pauta = _pauta(id="pauta-1")
    otra_pauta = _pauta(id="pauta-2")
    completa = _solicitud(pauta_id=pauta.id)
    pendiente = _solicitud(pauta_id=pauta.id)
    de_otra_pauta = _solicitud(pauta_id=otra_pauta.id)
    solicitudes = [completa, pendiente, de_otra_pauta]
    destinos = [_destino_publicado(completa), _destino_publicado(de_otra_pauta)]

    consumidas = PautaService().publicaciones_consumidas(pauta, solicitudes, destinos)

    assert consumidas == 1


def test_publicaciones_consumidas_counts_a_solicitud_with_several_destinos_once() -> None:
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta_id=pauta.id)
    destinos = [
        _destino_publicado(solicitud, canal=CanalPublicacion.WORDPRESS),
        _destino_publicado(
            solicitud,
            canal=CanalPublicacion.INSTAGRAM,
            url_publicacion="https://instagram.com/p/1",
        ),
    ]

    consumidas = PautaService().publicaciones_consumidas(pauta, [solicitud], destinos)

    assert consumidas == 1


def test_publicaciones_consumidas_excludes_a_solicitud_with_only_pending_destinos() -> None:
    pauta = _pauta(id="pauta-1")
    solicitud = _solicitud(pauta_id=pauta.id)
    destinos = [
        DestinoPublicacion(
            publication_request_id=solicitud.id,
            canal=CanalPublicacion.WORDPRESS,
            estado=EstadoDestino.PENDIENTE,
        )
    ]

    consumidas = PautaService().publicaciones_consumidas(pauta, [solicitud], destinos)

    assert consumidas == 0


def test_publicaciones_restantes_subtracts_consumed_from_contracted() -> None:
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=10)
    completa_1 = _solicitud(pauta_id=pauta.id)
    completa_2 = _solicitud(pauta_id=pauta.id)
    pendiente = _solicitud(pauta_id=pauta.id)
    solicitudes = [completa_1, completa_2, pendiente]
    destinos = [_destino_publicado(completa_1), _destino_publicado(completa_2)]

    restantes = PautaService().publicaciones_restantes(pauta, solicitudes, destinos)

    assert restantes == 8


def test_esta_vigente_is_true_within_the_contracted_range() -> None:
    pauta = _pauta(fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=lambda: date(2026, 8, 1))

    assert service.esta_vigente(pauta) is True


def test_esta_vigente_is_false_after_fecha_fin() -> None:
    pauta = _pauta(fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=lambda: date(2026, 8, 31))

    assert service.esta_vigente(pauta) is False


def test_esta_vencida_is_true_after_fecha_fin() -> None:
    pauta = _pauta(fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=lambda: date(2026, 8, 31))

    assert service.esta_vencida(pauta) is True


def test_esta_vencida_is_false_on_fecha_fin_itself() -> None:
    pauta = _pauta(fecha_inicio=date(2026, 7, 30), fecha_fin=date(2026, 8, 30))
    service = PautaService(clock=lambda: date(2026, 8, 30))

    assert service.esta_vencida(pauta) is False


def test_cuota_agotada_is_true_when_consumed_reaches_contracted() -> None:
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=2)
    s1 = _solicitud(pauta_id=pauta.id)
    s2 = _solicitud(pauta_id=pauta.id)
    destinos = [_destino_publicado(s1), _destino_publicado(s2)]

    assert PautaService().cuota_agotada(pauta, [s1, s2], destinos) is True


def test_cuota_agotada_is_false_below_contracted() -> None:
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=2)
    s1 = _solicitud(pauta_id=pauta.id)
    destinos = [_destino_publicado(s1)]

    assert PautaService().cuota_agotada(pauta, [s1], destinos) is False


def test_pautas_por_vencer_returns_only_pautas_within_the_window() -> None:
    vence_pronto = _pauta(id="pronto", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 5))
    vence_lejos = _pauta(id="lejos", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 12, 1))
    service = PautaService(clock=lambda: date(2026, 8, 1))

    resultado = service.pautas_por_vencer([vence_pronto, vence_lejos], dentro_de_dias=7)

    assert resultado == [vence_pronto]


def test_pautas_por_vencer_excludes_already_expired_pautas() -> None:
    vencida = _pauta(id="vencida", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 7, 1))
    service = PautaService(clock=lambda: date(2026, 8, 1))

    resultado = service.pautas_por_vencer([vencida], dentro_de_dias=30)

    assert resultado == []
