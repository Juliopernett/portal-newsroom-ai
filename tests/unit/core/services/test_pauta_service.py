"""Unit tests for PautaService, using in-memory Pauta/PublicationRequest data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
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


def test_publicaciones_consumidas_counts_only_published_requests_of_this_pauta() -> None:
    pauta = _pauta(id="pauta-1")
    otra_pauta = _pauta(id="pauta-2")
    solicitudes = [
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.RECIBIDA),
        _solicitud(pauta_id=otra_pauta.id, estado=PublicationRequestStatus.PUBLICADA),
    ]

    consumidas = PautaService().publicaciones_consumidas(pauta, solicitudes)

    assert consumidas == 1


def test_publicaciones_restantes_subtracts_consumed_from_contracted() -> None:
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=10)
    solicitudes = [
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.RECIBIDA),
    ]

    restantes = PautaService().publicaciones_restantes(pauta, solicitudes)

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
    solicitudes = [
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA),
    ]

    assert PautaService().cuota_agotada(pauta, solicitudes) is True


def test_cuota_agotada_is_false_below_contracted() -> None:
    pauta = _pauta(id="pauta-1", publicaciones_contratadas=2)
    solicitudes = [_solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.PUBLICADA)]

    assert PautaService().cuota_agotada(pauta, solicitudes) is False


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
