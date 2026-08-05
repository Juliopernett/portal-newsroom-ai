"""HTTP schemas for the Centro de Decisión (Sprint 5A).

Every field here mirrors what `core.analytics.DecisionEngineService`
already computes — no schema here introduces a computation of its own.
`ClientOut` is reused directly for every client reference, per the same
convention `app.api.schemas.dashboard` already follows.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.api.schemas.client import ClientOut
from core.analytics.decision_view_models import (
    AccionSugerida,
    AlertaSeveridad,
    AlertaTipo,
    NivelSalud,
    PatronComercialTipo,
)
from core.entities.pauta import PautaTipo


class ClienteScoreSaludOut(BaseModel):
    """One row of `GET /insights/salud-clientes`."""

    cliente: ClientOut
    score: int
    estrellas: int
    nivel: NivelSalud


class AlertaInteligenteOut(BaseModel):
    """One row of `GET /insights/centro-alertas`."""

    tipo: AlertaTipo
    severidad: AlertaSeveridad
    mensaje: str
    cliente: ClientOut | None
    accion: AccionSugerida
    dias: int | None = None


class ClienteRiesgoAbandonoOut(BaseModel):
    """One row of `GET /insights/riesgo-abandono`."""

    cliente: ClientOut
    dias_sin_actividad: int
    publicaciones_restantes: int
    fecha_vencimiento: date


class ClienteDormidoOut(BaseModel):
    """One row of `GET /insights/dormidos`."""

    cliente: ClientOut
    dias_sin_actividad: int
    ultimo_contrato_tipo: PautaTipo
    ultimo_contrato_fecha_fin: date


class OportunidadComercialOut(BaseModel):
    """One row of `GET /insights/oportunidades`."""

    cliente: ClientOut
    tipo: PatronComercialTipo
    mensaje: str
    racha: int | None = None
    tipo_habitual: PautaTipo | None = None
    porcentaje_consumido: Decimal | None = None
