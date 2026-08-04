"""HTTP schemas for the Dashboard Comercial (Sprint 4B).

Every field here mirrors what `core.analytics.AnalyticsService` already
returns — no schema here introduces a computation of its own. `ClientOut`
and `PublicationRequestOut` are reused directly for the alert lists and
the ranking's client column rather than redefined, per this sprint's
explicit instruction to reuse existing models where possible.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.api.schemas.client import ClientOut
from app.api.schemas.publication_request import PublicationRequestOut


class DashboardResumenOut(BaseModel):
    """Response body for `GET /dashboard/resumen` — Sección 1."""

    clientes_activos: int
    pautas_activas: int
    pautas_vencidas: int
    solicitudes_pendientes: int
    publicaciones_este_mes: int
    ingreso_contratado_activo: Decimal
    ingreso_historico: Decimal
    peso_comercial_promedio: Decimal


class DashboardAlertasOut(BaseModel):
    """Response body for `GET /dashboard/alertas` — Sección 2.

    Field order here is the alert categories' display priority (most
    severe first: exhausted quota, then expiring soon, then low quota,
    then a stale-request backlog) — not a re-sort of any list's contents,
    which stay in the order `AnalyticsService` already returns them.
    """

    clientes_cupo_agotado: list[ClientOut]
    clientes_por_vencer: list[ClientOut]
    clientes_cupo_bajo: list[ClientOut]
    solicitudes_antiguas: list[PublicationRequestOut]


class RankingComercialOut(BaseModel):
    """One row of `GET /dashboard/ranking` — Sección 3.

    Mirrors `core.analytics.view_models.RankingComercialItem` field for
    field — see that class's docstring for what `fecha_vencimiento` and
    `vigente` mean for a client with more than one Pauta.
    """

    cliente: ClientOut
    valor_contratado: Decimal
    peso_comercial: Decimal
    publicaciones_restantes: int
    fecha_vencimiento: date
    vigente: bool
