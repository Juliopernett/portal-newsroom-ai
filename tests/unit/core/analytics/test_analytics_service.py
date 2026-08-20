"""Unit tests for AnalyticsService, using in-memory Client/Pauta/PublicationRequest data."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from core.analytics.analytics_service import AnalyticsService
from core.analytics.view_models import EstadoComercial
from core.entities.client import Client, ClientType
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.pauta import Pauta
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


def _destino_publicado(solicitud: PublicationRequest, **overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": solicitud.id,
        "canal": CanalPublicacion.WORDPRESS,
        "estado": EstadoDestino.PUBLICADO,
        "fecha_publicacion": _AHORA,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def _solicitudes_completas(
    n: int, **overrides: object
) -> tuple[list[PublicationRequest], list[DestinoPublicacion]]:
    """Return `n` solicitudes plus one WORDPRESS/PUBLICADO destino each — the
    Sprint 4A, Increment 4 replacement for `estado=PublicationRequestStatus.PUBLICADA`
    (retired): "complete" is now `esta_completa` over a solicitud's own
    destinos, never the solicitud's own `estado`. Defaults `estado` to
    `ACEPTADA` — the real flow (`aceptar` then `marcar_publicado`, see
    `app.api.routers.publication_requests.publish_publication_request`)
    never leaves a completed solicitud at `RECIBIDA`.
    """
    defaults: dict[str, object] = {"estado": PublicationRequestStatus.ACEPTADA}
    defaults.update(overrides)
    solicitudes = [_solicitud(**defaults) for _ in range(n)]
    destinos = [_destino_publicado(s) for s in solicitudes]
    return solicitudes, destinos


def _service(
    clients: list[Client] | None = None,
    pautas: list[Pauta] | None = None,
    solicitudes: list[PublicationRequest] | None = None,
    destinos: list[DestinoPublicacion] | None = None,
) -> AnalyticsService:
    return AnalyticsService(
        clients=clients or [],
        pautas=pautas or [],
        solicitudes=solicitudes or [],
        destinos=destinos or [],
        clock=lambda: _AHORA,
    )


# ---------- Dashboard Ejecutivo ----------


def test_cantidad_clientes_counts_every_client_regardless_of_activity() -> None:
    clientes = [_client(id="c1"), _client(id="c2")]

    assert _service(clients=clientes).cantidad_clientes() == 2


def test_cantidad_clientes_activos_counts_only_clients_with_a_vigente_pauta() -> None:
    activo = _client(id="c1")
    inactivo = _client(id="c2")
    pautas = [
        _pauta(client_id="c1", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 30)),
        _pauta(client_id="c2", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 2, 1)),
    ]

    activos = _service(clients=[activo, inactivo], pautas=pautas).cantidad_clientes_activos()

    assert activos == 1


def test_cantidad_clientes_activos_counts_each_client_once_with_multiple_vigente_pautas() -> None:
    pautas = [
        _pauta(client_id="c1", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 30)),
        _pauta(client_id="c1", fecha_inicio=date(2026, 7, 15), fecha_fin=date(2026, 9, 1)),
    ]

    activos = _service(clients=[_client(id="c1")], pautas=pautas).cantidad_clientes_activos()

    assert activos == 1


def test_cantidad_pautas_vigentes_and_vencidas() -> None:
    vigente = _pauta(id="p1", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 30))
    vencida = _pauta(id="p2", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 2, 1))
    service = _service(pautas=[vigente, vencida])

    assert service.cantidad_pautas_vigentes() == 1
    assert service.cantidad_pautas_vencidas() == 1


def test_cantidad_publicaciones_pendientes_and_publicadas() -> None:
    pendiente = _solicitud(estado=PublicationRequestStatus.RECIBIDA)
    completas, destinos = _solicitudes_completas(2)
    service = _service(solicitudes=[pendiente, *completas], destinos=destinos)

    assert service.cantidad_publicaciones_pendientes() == 1
    assert service.cantidad_publicaciones_publicadas() == 2


def test_ingresos_anio_actual_sums_pautas_by_fecha_inicio_year_regardless_of_vigencia() -> None:
    vigente_este_anio = _pauta(
        fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 30), valor_pagado=Decimal("100")
    )
    vencida_este_anio = _pauta(
        fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 2, 1), valor_pagado=Decimal("50")
    )
    futura_este_anio = _pauta(
        fecha_inicio=date(2026, 12, 1), fecha_fin=date(2027, 1, 1), valor_pagado=Decimal("25")
    )
    de_otro_anio = _pauta(
        fecha_inicio=date(2025, 1, 1), fecha_fin=date(2025, 2, 1), valor_pagado=Decimal("999")
    )

    ingresos = _service(
        pautas=[vigente_este_anio, vencida_este_anio, futura_este_anio, de_otro_anio]
    ).ingresos_anio_actual()

    assert ingresos == Decimal("175")


def test_ingresos_historicos_sums_every_pauta() -> None:
    pautas = [_pauta(valor_pagado=Decimal("100")), _pauta(valor_pagado=Decimal("200"))]

    assert _service(pautas=pautas).ingresos_historicos() == Decimal("300")


def test_ingresos_historicos_is_zero_with_no_pautas() -> None:
    assert _service().ingresos_historicos() == Decimal("0")


# ---------- Reportes Comerciales ----------


def test_ranking_clientes_por_ingresos_sorts_descending_and_includes_zero_revenue() -> None:
    top = _client(id="top", nombre="Top")
    bottom = _client(id="bottom", nombre="Bottom")
    sin_pautas = _client(id="sin-pautas", nombre="Sin pautas")
    pautas = [
        _pauta(client_id="top", valor_pagado=Decimal("900")),
        _pauta(client_id="bottom", valor_pagado=Decimal("100")),
    ]

    service = _service(clients=[bottom, sin_pautas, top], pautas=pautas)
    ranking = service.ranking_clientes_por_ingresos()

    assert [item.cliente.id for item in ranking] == ["top", "bottom", "sin-pautas"]
    assert ranking[0].ingresos == Decimal("900")
    assert ranking[2].ingresos == Decimal("0")


def test_ranking_clientes_por_peso_comercial_excludes_clients_without_pautas() -> None:
    con_pauta = _client(id="con-pauta")
    sin_pauta = _client(id="sin-pauta")
    pautas = [_pauta(client_id="con-pauta")]

    ranking = _service(
        clients=[con_pauta, sin_pauta], pautas=pautas
    ).ranking_clientes_por_peso_comercial()

    assert [item.cliente.id for item in ranking] == ["con-pauta"]


def test_ranking_clientes_por_peso_comercial_uses_totals_not_average_of_ratios() -> None:
    # Un cliente con dos pautas muy distintas: 1000/10 y 100/10 -> promedio de
    # ratios daria (100+10)/2=55, pero sumando totales da 1100/20=55 tambien
    # en este caso simetrico; se prueba un caso asimetrico para diferenciar.
    pautas = [
        _pauta(client_id="c1", valor_pagado=Decimal("1000"), publicaciones_contratadas=100),
        _pauta(client_id="c1", valor_pagado=Decimal("100"), publicaciones_contratadas=1),
    ]
    # Promedio de ratios: (10 + 100) / 2 = 55.00
    # Totales: (1000+100) / (100+1) = 1100/101 = 10.891089... -> 10.89
    service = _service(clients=[_client(id="c1")], pautas=pautas)
    ranking = service.ranking_clientes_por_peso_comercial()

    assert ranking[0].peso_comercial == Decimal("10.89")


def test_ranking_clientes_por_peso_comercial_sorts_descending() -> None:
    pautas = [
        _pauta(client_id="bajo", valor_pagado=Decimal("10"), publicaciones_contratadas=10),
        _pauta(client_id="alto", valor_pagado=Decimal("1000"), publicaciones_contratadas=10),
    ]

    ranking = _service(
        clients=[_client(id="bajo"), _client(id="alto")], pautas=pautas
    ).ranking_clientes_por_peso_comercial()

    assert [item.cliente.id for item in ranking] == ["alto", "bajo"]


def test_clientes_por_vencer_returns_clients_with_a_pauta_expiring_soon() -> None:
    pronto = _client(id="pronto")
    lejos = _client(id="lejos")
    pautas = [
        _pauta(client_id="pronto", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 5)),
        _pauta(client_id="lejos", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 12, 1)),
    ]

    resultado = _service(clients=[pronto, lejos], pautas=pautas).clientes_por_vencer(dias=7)

    assert [c.id for c in resultado] == ["pronto"]


def test_clientes_con_cupo_agotado_returns_clients_with_an_exhausted_pauta() -> None:
    agotado = _client(id="agotado")
    con_cupo = _client(id="con-cupo")
    pautas = [
        _pauta(id="p1", client_id="agotado", publicaciones_contratadas=2),
        _pauta(id="p2", client_id="con-cupo", publicaciones_contratadas=2),
    ]
    de_p1, destinos_p1 = _solicitudes_completas(2, pauta_id="p1")
    de_p2, destinos_p2 = _solicitudes_completas(1, pauta_id="p2")
    solicitudes = [*de_p1, *de_p2]
    destinos = [*destinos_p1, *destinos_p2]

    resultado = _service(
        clients=[agotado, con_cupo], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).clientes_con_cupo_agotado()

    assert [c.id for c in resultado] == ["agotado"]


def test_clientes_con_cupo_agotado_excludes_an_agotada_but_vencida_pauta() -> None:
    # Sprint 4C: una pauta agotada que ya vencio no es tarea operativa.
    cliente = _client(id="c1")
    pauta_vencida = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        publicaciones_contratadas=2,
    )
    solicitudes, destinos = _solicitudes_completas(2, pauta_id="p1")

    resultado = _service(
        clients=[cliente], pautas=[pauta_vencida], solicitudes=solicitudes, destinos=destinos
    ).clientes_con_cupo_agotado()

    assert resultado == []


def test_clientes_con_cupo_bajo_uses_percentage_not_absolute_count() -> None:
    # 10 contratadas, 9 consumidas -> 1 restante -> 10% -> bajo cupo.
    bajo = _client(id="bajo")
    pautas = [_pauta(id="p1", client_id="bajo", publicaciones_contratadas=10)]
    solicitudes, destinos = _solicitudes_completas(9, pauta_id="p1")

    resultado = _service(
        clients=[bajo], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).clientes_con_cupo_bajo()

    assert [c.id for c in resultado] == ["bajo"]


def test_clientes_con_cupo_bajo_excludes_exactly_20_percent_remaining() -> None:
    # 10 contratadas, 8 consumidas -> 2 restantes -> exactamente 20% -> NO es bajo cupo.
    cliente = _client(id="c1")
    pautas = [_pauta(id="p1", client_id="c1", publicaciones_contratadas=10)]
    solicitudes, destinos = _solicitudes_completas(8, pauta_id="p1")

    resultado = _service(
        clients=[cliente], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).clientes_con_cupo_bajo()

    assert resultado == []


def test_clientes_con_cupo_bajo_excludes_a_low_quota_but_vencida_pauta() -> None:
    # Sprint 4C: mismo principio, para el 20%.
    cliente = _client(id="c1")
    pauta_vencida = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        publicaciones_contratadas=10,
    )
    solicitudes, destinos = _solicitudes_completas(9, pauta_id="p1")

    resultado = _service(
        clients=[cliente], pautas=[pauta_vencida], solicitudes=solicitudes, destinos=destinos
    ).clientes_con_cupo_bajo()

    assert resultado == []


# ---------- Reportes de Pautas ----------


def test_pautas_activas_and_vencidas() -> None:
    vigente = _pauta(id="p1", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 30))
    vencida = _pauta(id="p2", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 2, 1))
    service = _service(pautas=[vigente, vencida])

    assert service.pautas_activas() == [vigente]
    assert service.pautas_vencidas() == [vencida]


def test_pautas_por_vencer_delegates_to_pauta_service() -> None:
    pronto = _pauta(id="p1", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 8, 5))
    lejos = _pauta(id="p2", fecha_inicio=date(2026, 7, 1), fecha_fin=date(2026, 12, 1))

    resultado = _service(pautas=[pronto, lejos]).pautas_por_vencer(dias=7)

    assert resultado == [pronto]


def test_pautas_agotadas_returns_pautas_with_no_quota_left() -> None:
    agotada = _pauta(id="p1", publicaciones_contratadas=1)
    con_cupo = _pauta(id="p2", publicaciones_contratadas=5)
    solicitudes, destinos = _solicitudes_completas(1, pauta_id="p1")

    resultado = _service(
        pautas=[agotada, con_cupo], solicitudes=solicitudes, destinos=destinos
    ).pautas_agotadas()

    assert resultado == [agotada]


# ---------- Reportes Editoriales ----------


def test_solicitudes_pendientes_and_publicadas() -> None:
    recibida = _solicitud(id="s1", estado=PublicationRequestStatus.RECIBIDA)
    (publicada,), destinos = _solicitudes_completas(1, id="s2")
    service = _service(solicitudes=[recibida, publicada], destinos=destinos)

    assert service.solicitudes_pendientes() == [recibida]
    assert service.solicitudes_publicadas() == [publicada]


def test_solicitudes_pendientes_excludes_a_recibida_solicitud_that_is_already_completa() -> None:
    """Sprint 4A, Incremento 5: reachable when a destino is confirmed directly
    on a still-RECIBIDA solicitud (e.g. Instagram-only, no aceptar() call) —
    the API sets fecha_cierre via cerrar_si_completa the moment that happens,
    regardless of estado, so this solicitud must not keep showing up as
    "pending" forever."""
    recibida_completa = _solicitud(
        id="s1", estado=PublicationRequestStatus.RECIBIDA, fecha_cierre=_AHORA
    )
    genuinamente_pendiente = _solicitud(id="s2", estado=PublicationRequestStatus.RECIBIDA)
    service = _service(solicitudes=[recibida_completa, genuinamente_pendiente])

    assert service.solicitudes_pendientes() == [genuinamente_pendiente]


def test_solicitudes_antiguas_includes_requests_waiting_at_least_horas() -> None:
    justo_a_tiempo = _solicitud(id="s1", fecha_recepcion=datetime(2026, 8, 1, 8, 0, tzinfo=UTC))
    reciente = _solicitud(id="s2", fecha_recepcion=datetime(2026, 8, 1, 11, 0, tzinfo=UTC))

    resultado = _service(solicitudes=[justo_a_tiempo, reciente]).solicitudes_antiguas(horas=4)

    assert resultado == [justo_a_tiempo]


def test_solicitudes_antiguas_excludes_non_recibida_requests() -> None:
    (antigua_completa,), destinos = _solicitudes_completas(
        1,
        fecha_recepcion=datetime(2026, 8, 1, 1, 0, tzinfo=UTC),
        estado=PublicationRequestStatus.ACEPTADA,
        pauta_id="pauta-1",
    )

    resultado = _service(solicitudes=[antigua_completa], destinos=destinos).solicitudes_antiguas(
        horas=4
    )

    assert resultado == []


# ---------- Sprint 4B: métricas nuevas para el Dashboard Comercial ----------


def test_cantidad_publicaciones_publicadas_este_mes_counts_only_the_current_month() -> None:
    (este_mes,), destinos_este_mes = _solicitudes_completas(
        1, id="s1", fecha_recepcion=datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    )
    (mes_pasado,), destinos_mes_pasado = _solicitudes_completas(
        1, id="s2", fecha_recepcion=datetime(2026, 7, 31, 23, 59, tzinfo=UTC)
    )
    no_publicada = _solicitud(
        id="s3",
        estado=PublicationRequestStatus.RECIBIDA,
        fecha_recepcion=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
    )

    service = _service(
        solicitudes=[este_mes, mes_pasado, no_publicada],
        destinos=[*destinos_este_mes, *destinos_mes_pasado],
    )

    assert service.cantidad_publicaciones_publicadas_este_mes() == 1


def test_peso_comercial_promedio_averages_the_ranking() -> None:
    pautas = [
        _pauta(client_id="c1", valor_pagado=Decimal("100"), publicaciones_contratadas=10),
        _pauta(client_id="c2", valor_pagado=Decimal("300"), publicaciones_contratadas=10),
    ]
    service = _service(clients=[_client(id="c1"), _client(id="c2")], pautas=pautas)

    # pesos: 10.00 y 30.00 -> promedio 20.00
    assert service.peso_comercial_promedio() == Decimal("20.00")


def test_peso_comercial_promedio_is_zero_with_no_ranked_clients() -> None:
    assert _service().peso_comercial_promedio() == Decimal("0")


def test_clientes_con_menos_de_n_publicaciones_restantes_uses_an_absolute_count() -> None:
    # 10 contratadas, 8 publicadas -> 2 restantes -> bajo el minimo de 3.
    pocas = _client(id="pocas")
    pautas = [_pauta(id="p1", client_id="pocas", publicaciones_contratadas=10)]
    solicitudes, destinos = _solicitudes_completas(8, pauta_id="p1")

    resultado = _service(
        clients=[pocas], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).clientes_con_menos_de_n_publicaciones_restantes(minimo=3)

    assert [c.id for c in resultado] == ["pocas"]


def test_clientes_con_menos_de_n_publicaciones_restantes_excludes_exactly_the_minimum() -> None:
    # 10 contratadas, 7 publicadas -> 3 restantes -> no es "menos de 3".
    cliente = _client(id="c1")
    pautas = [_pauta(id="p1", client_id="c1", publicaciones_contratadas=10)]
    solicitudes, destinos = _solicitudes_completas(7, pauta_id="p1")

    resultado = _service(
        clients=[cliente], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).clientes_con_menos_de_n_publicaciones_restantes(minimo=3)

    assert resultado == []


def test_clientes_con_menos_de_n_publicaciones_restantes_excludes_a_vencida_pauta() -> None:
    # Sprint 4C: la razon del cambio -- ya no mezcla vigentes y vencidas.
    cliente = _client(id="c1")
    pauta_vencida = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        publicaciones_contratadas=10,
    )
    solicitudes, destinos = _solicitudes_completas(9, pauta_id="p1")

    resultado = _service(
        clients=[cliente], pautas=[pauta_vencida], solicitudes=solicitudes, destinos=destinos
    ).clientes_con_menos_de_n_publicaciones_restantes(minimo=3)

    assert resultado == []


def test_clientes_con_publicaciones_individuales_pendientes_filters_by_tipo_y_saldo() -> None:
    individual_con_saldo = _client(id="individual")
    individual_agotado = _client(id="agotado")
    paquete = _client(id="paquete")
    pautas = [
        _pauta(
            id="p1",
            client_id="individual",
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 2),
            publicaciones_contratadas=3,
        ),
        _pauta(
            id="p2",
            client_id="agotado",
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 2),
            publicaciones_contratadas=1,
        ),
        _pauta(
            id="p3",
            client_id="paquete",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 30),
            publicaciones_contratadas=8,
        ),
    ]
    solicitudes, destinos = _solicitudes_completas(1, pauta_id="p2")

    resultado = _service(
        clients=[individual_con_saldo, individual_agotado, paquete],
        pautas=pautas,
        solicitudes=solicitudes,
        destinos=destinos,
    ).clientes_con_publicaciones_individuales_pendientes()

    assert [c.id for c in resultado] == ["individual"]


def test_clientes_con_contrato_por_renovar_excludes_individual_pautas() -> None:
    paquete_por_vencer = _client(id="paquete")
    individual_por_vencer = _client(id="individual")
    pautas = [
        _pauta(
            id="p1",
            client_id="paquete",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 5),
            publicaciones_contratadas=8,
        ),
        _pauta(
            id="p2",
            client_id="individual",
            fecha_inicio=date(2026, 7, 30),
            fecha_fin=date(2026, 8, 5),
            publicaciones_contratadas=2,
        ),
    ]

    resultado = _service(
        clients=[paquete_por_vencer, individual_por_vencer], pautas=pautas
    ).clientes_con_contrato_por_renovar(dias=7)

    assert [c.id for c in resultado] == ["paquete"]


def test_clientes_con_publicaciones_sin_usar_returns_only_vencidas_con_saldo() -> None:
    dejo_saldo = _client(id="dejo-saldo")
    vencida_sin_saldo = _client(id="sin-saldo")
    vigente = _client(id="vigente")
    pautas = [
        _pauta(
            id="p1",
            client_id="dejo-saldo",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            publicaciones_contratadas=8,
        ),
        _pauta(
            id="p2",
            client_id="sin-saldo",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            publicaciones_contratadas=1,
        ),
        _pauta(
            id="p3",
            client_id="vigente",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 30),
            publicaciones_contratadas=8,
        ),
    ]
    solicitudes, destinos = _solicitudes_completas(1, pauta_id="p2")

    resultado = _service(
        clients=[dejo_saldo, vencida_sin_saldo, vigente],
        pautas=pautas,
        solicitudes=solicitudes,
        destinos=destinos,
    ).clientes_con_publicaciones_sin_usar()

    assert [c.id for c in resultado] == ["dejo-saldo"]


def test_valor_promedio_por_cliente_divides_ingresos_by_client_count() -> None:
    pautas = [
        _pauta(client_id="c1", valor_pagado=Decimal("100")),
        _pauta(client_id="c2", valor_pagado=Decimal("300")),
    ]

    service = _service(clients=[_client(id="c1"), _client(id="c2")], pautas=pautas)

    assert service.valor_promedio_por_cliente() == Decimal("200.00")


def test_valor_promedio_por_cliente_is_zero_with_no_clients() -> None:
    assert _service().valor_promedio_por_cliente() == Decimal("0")


def test_clientes_premium_returns_only_semestral_and_anual() -> None:
    mensual = _client(id="mensual")
    semestral = _client(id="semestral")
    anual = _client(id="anual")
    pautas = [
        _pauta(
            id="p1",
            client_id="mensual",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
        ),
        _pauta(
            id="p2",
            client_id="semestral",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2027, 1, 1),
        ),
        _pauta(
            id="p3",
            client_id="anual",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2027, 7, 10),
        ),
    ]

    resultado = _service(clients=[mensual, semestral, anual], pautas=pautas).clientes_premium()

    assert {c.id for c in resultado} == {"semestral", "anual"}


def test_ranking_comercial_uses_only_the_current_contract_not_a_sum() -> None:
    # Funcional review 2026-08-05: publicaciones_contratadas/restantes/
    # fecha_vencimiento deben venir SOLO del contrato de referencia (la
    # vigente), nunca de sumar una pauta vencida con la vigente actual
    # -- eso implicaria un saldo de publicaciones que no existe.
    cliente = _client(id="c1")
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 30),
            publicaciones_contratadas=10,
            valor_pagado=Decimal("100"),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            publicaciones_contratadas=5,
            valor_pagado=Decimal("50"),
        ),
    ]
    solicitudes, destinos = _solicitudes_completas(1, pauta_id="p1")

    service = _service(clients=[cliente], pautas=pautas, solicitudes=solicitudes, destinos=destinos)
    ranking = service.ranking_comercial()

    assert len(ranking) == 1
    item = ranking[0]
    assert item.cliente.id == "c1"
    # valor_contratado y peso_comercial SI son sumas de por vida -- el
    # dinero ya pagado no "vence" como el cupo de publicaciones.
    assert item.valor_contratado == Decimal("150")
    assert item.peso_comercial == Decimal("10.00")
    # p1 es el contrato de referencia (la unica vigente): 10 contratadas,
    # 9 restantes (10-1 publicada), vence 2026-08-30 -- nunca sumado con
    # las 5 de p2, que ya vencio.
    assert item.publicaciones_contratadas == 10
    assert item.publicaciones_restantes == 9
    assert item.fecha_vencimiento == date(2026, 8, 30)
    assert item.vigente is True
    assert item.estado_comercial == EstadoComercial.SALUDABLE
    assert item.pauta_id == "p1"


def test_ranking_comercial_falls_back_to_the_most_recent_pauta_when_none_vigente() -> None:
    cliente = _client(id="c1")
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            publicaciones_contratadas=5,
            valor_pagado=Decimal("50"),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 4, 1),
            publicaciones_contratadas=8,
            valor_pagado=Decimal("80"),
        ),
    ]

    item = _service(clients=[cliente], pautas=pautas).ranking_comercial()[0]

    # Ninguna vigente -- usa la que empezo mas reciente (p2), no la mas
    # antigua, para que el "ultimo contrato conocido" sea el mas util.
    assert item.publicaciones_contratadas == 8
    assert item.fecha_vencimiento == date(2026, 4, 1)
    assert item.vigente is False
    assert item.estado_comercial == EstadoComercial.VENCIDO
    assert item.pauta_id == "p2"


def test_ranking_comercial_prefers_the_most_recently_started_vigente_pauta() -> None:
    cliente = _client(id="c1")
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 12, 1),
            publicaciones_contratadas=5,
            valor_pagado=Decimal("50"),
        ),
        _pauta(
            id="p2",
            client_id="c1",
            fecha_inicio=date(2026, 7, 15),
            fecha_fin=date(2026, 12, 15),
            publicaciones_contratadas=8,
            valor_pagado=Decimal("80"),
        ),
    ]

    item = _service(clients=[cliente], pautas=pautas).ranking_comercial()[0]

    # Ambas vigentes hoy -- gana la que empezo mas tarde (p2).
    assert item.publicaciones_contratadas == 8
    assert item.fecha_vencimiento == date(2026, 12, 15)


def test_ranking_comercial_excludes_clients_without_pautas() -> None:
    sin_pautas = _client(id="sin-pautas")

    assert _service(clients=[sin_pautas]).ranking_comercial() == []


def test_ranking_comercial_is_sorted_by_peso_comercial_descending() -> None:
    pautas = [
        _pauta(client_id="bajo", valor_pagado=Decimal("10"), publicaciones_contratadas=10),
        _pauta(client_id="alto", valor_pagado=Decimal("1000"), publicaciones_contratadas=10),
    ]

    ranking = _service(
        clients=[_client(id="bajo"), _client(id="alto")], pautas=pautas
    ).ranking_comercial()

    assert [item.cliente.id for item in ranking] == ["alto", "bajo"]


# ---------- estado_comercial (Sprint 4C) ----------


def test_estado_comercial_is_vencido_when_no_pauta_is_vigente() -> None:
    pautas = [
        _pauta(
            client_id="c1",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 2, 1),
            publicaciones_contratadas=8,
        )
    ]

    ranking = _service(clients=[_client(id="c1")], pautas=pautas).ranking_comercial()

    assert ranking[0].estado_comercial == EstadoComercial.VENCIDO


def test_estado_comercial_is_renovacion_when_quota_is_exhausted() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 1),
            publicaciones_contratadas=2,
        )
    ]
    solicitudes, destinos = _solicitudes_completas(2, pauta_id="p1")

    ranking = _service(
        clients=[_client(id="c1")], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).ranking_comercial()

    assert ranking[0].estado_comercial == EstadoComercial.RENOVACION


def test_estado_comercial_is_renovacion_when_expiring_within_7_days() -> None:
    pautas = [
        _pauta(
            client_id="c1",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 8, 5),  # 4 dias despues de "hoy" (2026-08-01)
            publicaciones_contratadas=50,
        )
    ]

    ranking = _service(clients=[_client(id="c1")], pautas=pautas).ranking_comercial()

    assert ranking[0].estado_comercial == EstadoComercial.RENOVACION


def test_estado_comercial_is_atencion_when_restantes_is_low_but_not_urgent() -> None:
    pautas = [
        _pauta(
            id="p1",
            client_id="c1",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 1),
            publicaciones_contratadas=10,
        )
    ]
    solicitudes, destinos = _solicitudes_completas(7, pauta_id="p1")  # 3 restantes

    ranking = _service(
        clients=[_client(id="c1")], pautas=pautas, solicitudes=solicitudes, destinos=destinos
    ).ranking_comercial()

    assert ranking[0].estado_comercial == EstadoComercial.ATENCION


def test_estado_comercial_is_saludable_with_plenty_of_time_and_quota() -> None:
    pautas = [
        _pauta(
            client_id="c1",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 1),
            publicaciones_contratadas=10,
        )
    ]

    ranking = _service(clients=[_client(id="c1")], pautas=pautas).ranking_comercial()

    assert ranking[0].estado_comercial == EstadoComercial.SALUDABLE


def test_estado_comercial_ignores_leftover_quota_from_a_vencida_pauta() -> None:
    # Una pauta vieja y ya vencida con mucho saldo sin usar no debe "tapar"
    # que la pauta vigente actual esta casi agotada.
    vencida_con_saldo = _pauta(
        id="p1",
        client_id="c1",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
        publicaciones_contratadas=20,
    )
    vigente_casi_agotada = _pauta(
        id="p2",
        client_id="c1",
        fecha_inicio=date(2026, 7, 1),
        fecha_fin=date(2026, 12, 1),
        publicaciones_contratadas=2,
    )
    solicitudes, destinos = _solicitudes_completas(1, pauta_id="p2")

    ranking = _service(
        clients=[_client(id="c1")],
        pautas=[vencida_con_saldo, vigente_casi_agotada],
        solicitudes=solicitudes,
        destinos=destinos,
    ).ranking_comercial()

    item = ranking[0]
    # Tanto publicaciones_restantes como estado_comercial miran SOLO la
    # vigente (1 restante) -- el saldo de la vencida (20) no la "tapa".
    assert item.publicaciones_restantes == 1
    assert item.estado_comercial == EstadoComercial.ATENCION


# ---------- solicitudes_pendientes_priorizadas (Sprint 4C, 2026-08-05) ----------


def test_solicitudes_pendientes_priorizadas_matches_the_business_example() -> None:
    # Ejemplo literal de la regla: prioridad manual > peso comercial > fecha.
    pautas = [
        _pauta(id="pa", client_id="a", valor_pagado=Decimal("25000"), publicaciones_contratadas=1),
        _pauta(id="pb", client_id="b", valor_pagado=Decimal("73150"), publicaciones_contratadas=1),
        _pauta(id="pc", client_id="c", valor_pagado=Decimal("50000"), publicaciones_contratadas=1),
        _pauta(id="pd", client_id="d", valor_pagado=Decimal("50000"), publicaciones_contratadas=1),
    ]
    solicitudes = [
        _solicitud(
            id="A",
            pauta_id="pa",
            prioridad_manual=True,
            fecha_recepcion=datetime(2026, 8, 1, 10, 30, tzinfo=UTC),
        ),
        _solicitud(id="B", pauta_id="pb", fecha_recepcion=datetime(2026, 8, 1, 9, 0, tzinfo=UTC)),
        _solicitud(id="C", pauta_id="pc", fecha_recepcion=datetime(2026, 8, 1, 8, 30, tzinfo=UTC)),
        _solicitud(id="D", pauta_id="pd", fecha_recepcion=datetime(2026, 8, 1, 8, 0, tzinfo=UTC)),
    ]

    service = _service(pautas=pautas, solicitudes=solicitudes)
    resultado = service.solicitudes_pendientes_priorizadas()

    assert [s.id for s in resultado] == ["A", "B", "D", "C"]


def test_solicitudes_pendientes_priorizadas_treats_an_unlinked_solicitud_as_zero_peso() -> None:
    pauta = _pauta(id="p1", client_id="c1", valor_pagado=Decimal("1"), publicaciones_contratadas=1)
    con_pauta = _solicitud(
        id="con-pauta", pauta_id="p1", fecha_recepcion=datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    )
    sin_pauta = _solicitud(
        id="sin-pauta", pauta_id=None, fecha_recepcion=datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
    )

    resultado = _service(
        pautas=[pauta], solicitudes=[con_pauta, sin_pauta]
    ).solicitudes_pendientes_priorizadas()

    # sin_pauta llegó primero, pero al no tener pauta cuenta como $0 de peso
    # comercial -- con_pauta (peso $1.00) va primero.
    assert [s.id for s in resultado] == ["con-pauta", "sin-pauta"]


def test_solicitudes_pendientes_priorizadas_excludes_non_recibida() -> None:
    recibida = _solicitud(id="r", estado=PublicationRequestStatus.RECIBIDA)
    (aceptada,), destinos = _solicitudes_completas(
        1, id="p", estado=PublicationRequestStatus.ACEPTADA
    )

    resultado = _service(
        solicitudes=[recibida, aceptada], destinos=destinos
    ).solicitudes_pendientes_priorizadas()

    assert [s.id for s in resultado] == ["r"]
