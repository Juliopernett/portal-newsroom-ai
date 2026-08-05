"""Unit tests for DecisionEngineService, using in-memory Client/Pauta/PublicationRequest data."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from core.analytics.decision_engine import DecisionEngineService
from core.analytics.decision_view_models import (
    AccionSugerida,
    AlertaSeveridad,
    AlertaTipo,
    NivelSalud,
    PatronComercialTipo,
)
from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta, PautaTipo
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus

_HOY = date(2026, 8, 1)
_AHORA = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def _client(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Cliente de prueba",
        "tipo": ClientType.ARTISTA,
        "telefono": "3000000000",
    }
    defaults.update(overrides)
    return Client(**defaults)


def _pauta(**overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": "client-1",
        "fecha_inicio": date(2026, 7, 1),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000"),
        "fecha_pago": date(2026, 7, 1),
        "fecha_registro": _AHORA,
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {
        "pauta_id": "pauta-1",
        "texto": "Solicitud de ejemplo",
        "fecha_recepcion": _AHORA,
    }
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def _service(
    clients: list[Client] | None = None,
    pautas: list[Pauta] | None = None,
    solicitudes: list[PublicationRequest] | None = None,
) -> DecisionEngineService:
    return DecisionEngineService(
        clients=clients or [],
        pautas=pautas or [],
        solicitudes=solicitudes or [],
        clock=lambda: _AHORA,
    )


# ---------- Última actividad / Riesgo de Abandono / Dormidos ----------


def test_riesgo_abandono_flags_vigente_client_with_quota_and_long_silence() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 9, 1),
        publicaciones_contratadas=20,
        fecha_registro=_AHORA - timedelta(days=40),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    riesgo = service.clientes_riesgo_abandono()

    assert len(riesgo) == 1
    assert riesgo[0].cliente.id == "c1"
    assert riesgo[0].dias_sin_actividad == 40
    assert riesgo[0].publicaciones_restantes == 20


def test_riesgo_abandono_excludes_client_active_recently() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 9, 1),
        fecha_registro=_AHORA - timedelta(days=2),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    assert service.clientes_riesgo_abandono() == []


def test_riesgo_abandono_excludes_client_with_exhausted_quota() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 9, 1),
        publicaciones_contratadas=2,
        fecha_registro=_AHORA - timedelta(days=40),
    )
    solicitudes = [
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA),
    ]
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=solicitudes)

    assert service.clientes_riesgo_abandono() == []


def test_riesgo_abandono_excludes_client_with_no_vigente_pauta() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        fecha_registro=_AHORA - timedelta(days=90),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    assert service.clientes_riesgo_abandono() == []


def test_dormidos_flags_client_with_no_vigente_pauta_and_long_silence() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        fecha_registro=_AHORA - timedelta(days=90),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    dormidos = service.clientes_dormidos()

    assert len(dormidos) == 1
    assert dormidos[0].cliente.id == "c1"
    assert dormidos[0].dias_sin_actividad == 90
    assert dormidos[0].ultimo_contrato.id == "p1"


def test_dormidos_excludes_client_with_one_vigente_pauta_even_with_other_stale_ones() -> None:
    cliente = _client(id="c1")
    vieja = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        fecha_registro=_AHORA - timedelta(days=180),
    )
    vigente = _pauta(
        id="p2",
        client_id="c1",
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=date(2026, 8, 30),
        fecha_registro=_AHORA - timedelta(days=1),
    )
    service = _service(clients=[cliente], pautas=[vieja, vigente])

    assert service.clientes_dormidos() == []


def test_dormidos_excludes_client_with_no_pauta_at_all() -> None:
    cliente = _client(id="c1")

    assert _service(clients=[cliente]).clientes_dormidos() == []


def test_ultima_actividad_uses_solicitud_when_more_recent_than_pauta_registro() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 9, 1),
        publicaciones_contratadas=20,
        fecha_registro=_AHORA - timedelta(days=40),
    )
    solicitud_reciente = _solicitud(pauta_id="p1", fecha_recepcion=_AHORA - timedelta(days=3))
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=[solicitud_reciente])

    # Actividad reciente (3 días) saca al cliente de Riesgo de Abandono.
    assert service.clientes_riesgo_abandono() == []


# ---------- Cadena de renovaciones ----------


def test_racha_renovaciones_counts_consecutive_time_package_pautas() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 31),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 2, 2),
            fecha_fin=date(2026, 3, 4),
        ),
        _pauta(
            id="p3",
            client_id="c1",
            fecha_inicio=date(2026, 3, 5),
            fecha_fin=date(2026, 4, 4),
        ),
    ]
    service = _service(pautas=pautas)

    assert service.racha_renovaciones("c1") == 2


def test_racha_renovaciones_is_cut_by_large_gap() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 31),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 7, 1),
        ),
    ]
    service = _service(pautas=pautas)

    assert service.racha_renovaciones("c1") == 0


def test_racha_renovaciones_counts_overlapping_pautas_as_continuous() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 15),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 3, 4),
        ),
    ]
    service = _service(pautas=pautas)

    assert service.racha_renovaciones("c1") == 1


def test_racha_renovaciones_is_zero_when_most_recent_pauta_is_individual() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 31),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 2, 5),
            fecha_fin=date(2026, 2, 10),
        ),
    ]
    service = _service(pautas=pautas)

    assert service.racha_renovaciones("c1") == 0


def test_racha_renovaciones_is_zero_with_no_pautas() -> None:
    assert _service().racha_renovaciones("c1") == 0


# ---------- Score de Salud ----------


def test_score_salud_cliente_is_none_without_any_pauta() -> None:
    cliente = _client(id="c1")

    assert _service(clients=[cliente]).score_salud_cliente("c1") is None


def test_score_salud_cliente_is_high_for_healthy_vigente_client() -> None:
    """A contract that just started (full quota, plenty of runway) preceded by
    4 contiguous renewals and no pending backlog should max out every signal.
    """
    cliente = _client(id="c1")
    pautas = [
        _pauta(id="p1", client_id="c1", fecha_inicio=date(2026, 1, 31), fecha_fin=date(2026, 3, 2)),
        _pauta(id="p2", client_id="c1", fecha_inicio=date(2026, 3, 17), fecha_fin=date(2026, 4, 17)),
        _pauta(id="p3", client_id="c1", fecha_inicio=date(2026, 5, 2), fecha_fin=date(2026, 6, 2)),
        _pauta(id="p4", client_id="c1", fecha_inicio=date(2026, 6, 17), fecha_fin=date(2026, 7, 17)),
        _pauta(
            id="p5",
            client_id="c1",
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 9, 15),
            publicaciones_contratadas=10,
        ),
    ]
    service = _service(clients=[cliente], pautas=pautas)

    assert service.racha_renovaciones("c1") == 4

    resultado = service.score_salud_cliente("c1")

    assert resultado is not None
    assert resultado.score >= 85
    assert resultado.nivel is NivelSalud.EXCELENTE
    assert resultado.estrellas == 5


def test_score_salud_cliente_is_low_for_vencido_client_with_no_history() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        fecha_registro=_AHORA - timedelta(days=90),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    resultado = service.score_salud_cliente("c1")

    assert resultado is not None
    assert resultado.nivel in (NivelSalud.RIESGO, NivelSalud.CRITICO)


def test_scores_salud_sorts_worst_first() -> None:
    sano = _client(id="c-sano")
    vencido = _client(id="c-vencido")
    pautas = [
        _pauta(
            id="p-sano",
            client_id="c-sano",
            fecha_inicio=date(2026, 7, 15),
            fecha_fin=date(2026, 9, 15),
            fecha_registro=_AHORA - timedelta(days=1),
        ),
        _pauta(
            id="p-vencido",
            client_id="c-vencido",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            fecha_registro=_AHORA - timedelta(days=90),
        ),
    ]
    service = _service(clients=[sano, vencido], pautas=pautas)

    scores = service.scores_salud()

    assert [s.cliente.id for s in scores] == ["c-vencido", "c-sano"]


# ---------- Oportunidades Comerciales (patrones finos) ----------


def test_clientes_consumo_alto_flags_vigente_pauta_at_90_percent_or_more() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=date(2026, 8, 30),
        publicaciones_contratadas=10,
    )
    solicitudes = [
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA) for _ in range(9)
    ]
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=solicitudes)

    resultado = service.clientes_consumo_alto()

    assert len(resultado) == 1
    assert resultado[0].tipo is PatronComercialTipo.CONSUMO_ALTO
    assert resultado[0].porcentaje_consumido == Decimal("90")


def test_clientes_consumo_alto_excludes_fully_exhausted_pauta() -> None:
    cliente = _client(id="c1")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=date(2026, 8, 30),
        publicaciones_contratadas=10,
    )
    solicitudes = [
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA) for _ in range(10)
    ]
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=solicitudes)

    assert service.clientes_consumo_alto() == []


def test_clientes_nunca_premium_excludes_client_with_any_historical_premium_pauta() -> None:
    cliente = _client(id="c1")
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2025, 1, 1),
            fecha_fin=date(2025, 7, 1),
        ),
    ]
    service = _service(clients=[cliente], pautas=pautas)

    assert service.clientes_nunca_premium() == []


def test_clientes_nunca_premium_flags_client_with_only_mensual_pautas() -> None:
    cliente = _client(id="c1")
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 31),
        ),
    ]
    service = _service(clients=[cliente], pautas=pautas)

    resultado = service.clientes_nunca_premium()

    assert len(resultado) == 1
    assert resultado[0].tipo is PatronComercialTipo.NUNCA_PREMIUM


def test_clientes_recurrencia_mensual_requires_three_consecutive_mensual_pautas() -> None:
    pautas = [
        _pauta(id="p1", client_id="c1", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 1, 31)),
        _pauta(id="p2", client_id="c1", fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 3, 3)),
        _pauta(id="p3", client_id="c1", fecha_inicio=date(2026, 3, 4), fecha_fin=date(2026, 4, 3)),
    ]
    service = _service(clients=[_client(id="c1")], pautas=pautas)

    resultado = service.clientes_recurrencia_mensual()

    assert len(resultado) == 1
    assert resultado[0].tipo is PatronComercialTipo.RECURRENCIA_MENSUAL


def test_clientes_racha_renovaciones_uses_default_minimum_of_three() -> None:
    pautas = [
        _pauta(id="p1", client_id="c1", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 1, 31)),
        _pauta(id="p2", client_id="c1", fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 3, 3)),
    ]
    service = _service(clients=[_client(id="c1")], pautas=pautas)

    assert service.clientes_racha_renovaciones() == []
    assert service.clientes_racha_renovaciones(minimo=1)[0].racha == 1


def test_clientes_tipo_habitual_requires_strict_majority() -> None:
    empatado = [
        _pauta(id="p1", client_id="c1", fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 1, 31)),
        _pauta(id="p2", client_id="c1", fecha_inicio=date(2025, 3, 1), fecha_fin=date(2025, 5, 30)),
    ]
    service = _service(clients=[_client(id="c1")], pautas=empatado)

    assert service.clientes_tipo_habitual() == []


def test_clientes_tipo_habitual_flags_dominant_type() -> None:
    pautas = [
        _pauta(id="p1", client_id="c1", fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 1, 31)),
        _pauta(id="p2", client_id="c1", fecha_inicio=date(2025, 3, 1), fecha_fin=date(2025, 3, 31)),
        _pauta(id="p3", client_id="c1", fecha_inicio=date(2025, 5, 1), fecha_fin=date(2025, 7, 30)),
    ]
    service = _service(clients=[_client(id="c1")], pautas=pautas)

    resultado = service.clientes_tipo_habitual()

    assert len(resultado) == 1
    assert resultado[0].tipo_habitual is PautaTipo.MENSUAL


# ---------- Centro de Alertas Inteligentes ----------


def test_centro_alertas_orders_by_severity_then_dias() -> None:
    cliente_agotado = _client(id="c-agotado", nombre="Agotado")
    cliente_vence_hoy = _client(id="c-hoy", nombre="Vence Hoy")
    pautas = [
        _pauta(
            id="p-agotado",
            client_id="c-agotado",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 30),
            publicaciones_contratadas=2,
        ),
        _pauta(
            id="p-hoy",
            client_id="c-hoy",
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 8, 1),
            publicaciones_contratadas=20,
        ),
    ]
    solicitudes = [
        _solicitud(pauta_id="p-agotado", estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id="p-agotado", estado=PublicationRequestStatus.PUBLICADA),
    ]
    service = _service(
        clients=[cliente_agotado, cliente_vence_hoy], pautas=pautas, solicitudes=solicitudes
    )

    alertas = service.centro_alertas()

    assert [a.tipo for a in alertas] == [AlertaTipo.CUPO_AGOTADO, AlertaTipo.POR_VENCER]
    assert alertas[0].severidad is AlertaSeveridad.CRITICA
    assert alertas[0].accion is AccionSugerida.RENOVAR


def test_centro_alertas_does_not_repeat_a_client_across_categories() -> None:
    cliente = _client(id="c1", nombre="Unico")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=date(2026, 8, 30),
        publicaciones_contratadas=2,
    )
    solicitudes = [
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA),
        _solicitud(pauta_id="p1", estado=PublicationRequestStatus.PUBLICADA),
    ]
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=solicitudes)

    alertas = service.centro_alertas()

    ids = [a.cliente.id for a in alertas if a.cliente is not None]
    assert ids.count("c1") == 1


def test_centro_alertas_includes_material_recibido_for_recent_request() -> None:
    cliente = _client(id="c1", nombre="Recien Enviado")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 12, 1),
        publicaciones_contratadas=20,
    )
    solicitud = _solicitud(
        pauta_id="p1",
        estado=PublicationRequestStatus.RECIBIDA,
        fecha_recepcion=_AHORA - timedelta(hours=2),
    )
    service = _service(clients=[cliente], pautas=[pauta], solicitudes=[solicitud])

    alertas = service.centro_alertas()

    assert any(a.tipo is AlertaTipo.MATERIAL_RECIBIDO for a in alertas)


def test_centro_alertas_includes_riesgo_abandono() -> None:
    cliente = _client(id="c1", nombre="Silencioso")
    pauta = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 6, 1),
        fecha_fin=date(2026, 12, 1),
        publicaciones_contratadas=20,
        fecha_registro=_AHORA - timedelta(days=20),
    )
    service = _service(clients=[cliente], pautas=[pauta])

    alertas = service.centro_alertas()

    riesgo = [a for a in alertas if a.tipo is AlertaTipo.RIESGO_ABANDONO]
    assert len(riesgo) == 1
    assert riesgo[0].accion is AccionSugerida.CONTACTAR


def test_centro_alertas_is_empty_with_no_data() -> None:
    assert _service().centro_alertas() == []
