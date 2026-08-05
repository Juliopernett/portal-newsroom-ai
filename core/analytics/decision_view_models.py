"""Read-only view models returned by `DecisionEngineService`.

Sibling of `core.analytics.view_models`, kept separate rather than merged
into it: that file documents the outputs of `AnalyticsService` (raw
business facts — counts, rankings, lists). Everything here instead carries
a Sprint 5A judgment call — a scoring formula's weights, an inactivity
threshold, a severity ranking, pre-written Spanish copy — that is
deliberately calibrated, not derived, and explicitly expected to be
retuned once the business has used it. Keeping that vocabulary in its own
file makes it obvious at a glance which of the two kinds of "computed
value" a given dataclass is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from core.entities.client import Client
from core.entities.pauta import Pauta, PautaTipo


class NivelSalud(StrEnum):
    """A Client's health-score bucket — see `DecisionEngineService.score_salud_cliente`.

    Cut points (85/70/50/30) are a Sprint 5A calibration, not a derived
    business rule — adjust freely once the business has seen real scores
    against real outcomes.
    """

    EXCELENTE = "excelente"
    BUENO = "bueno"
    REGULAR = "regular"
    RIESGO = "riesgo"
    CRITICO = "critico"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClienteScoreSalud:
    """A `Client`'s health score (0-100), star rating (0-5) and bucket.

    Only produced for a `Client` with at least one `Pauta` — see
    `DecisionEngineService.scores_salud`.
    """

    cliente: Client
    score: int
    estrellas: int
    nivel: NivelSalud


class AlertaSeveridad(StrEnum):
    """How urgently a `AlertaInteligente` needs the team's attention today."""

    CRITICA = "critica"
    ATENCION = "atencion"
    INFORMATIVA = "informativa"


class AlertaTipo(StrEnum):
    """What kind of signal produced a `AlertaInteligente` — for frontend icon/grouping only."""

    CUPO_AGOTADO = "cupo_agotado"
    POR_VENCER = "por_vencer"
    MENOS_DE_N_RESTANTES = "menos_de_n_restantes"
    SIN_ACTIVIDAD_RECIENTE = "sin_actividad_reciente"
    MATERIAL_RECIBIDO = "material_recibido"
    RIESGO_ABANDONO = "riesgo_abandono"
    SOLICITUD_ANTIGUA = "solicitud_antigua"


class AccionSugerida(StrEnum):
    """The one action the frontend should offer for a `AlertaInteligente`.

    A closed set on purpose — the frontend maps each value to exactly one
    button (label + click handler) instead of inferring which button to
    show from ad hoc fields, the way `app.js`'s `computarAccionesHoy` did
    before this existed.
    """

    RENOVAR = "renovar"
    CONTACTAR = "contactar"
    REACTIVAR = "reactivar"
    VER_CLIENTE = "ver_cliente"
    VER_SOLICITUDES = "ver_solicitudes"
    NINGUNA = "ninguna"


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertaInteligente:
    """One row of the Centro de Alertas — a single, already-written task.

    `cliente` is `None` for alerts about the editorial backlog rather than
    a specific client (e.g. an unlinked stale request) — `accion` is
    `VER_SOLICITUDES` in that case, never one of the client-scoped actions.
    """

    tipo: AlertaTipo
    severidad: AlertaSeveridad
    mensaje: str
    cliente: Client | None
    accion: AccionSugerida
    dias: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ClienteRiesgoAbandono:
    """A `Client` with a vigente, unexhausted `Pauta` who has gone quiet.

    See `DecisionEngineService.clientes_riesgo_abandono` for the exact
    definition and threshold.
    """

    cliente: Client
    dias_sin_actividad: int
    publicaciones_restantes: int
    fecha_vencimiento: date


@dataclass(frozen=True, slots=True, kw_only=True)
class ClienteDormido:
    """A `Client` with no vigente `Pauta` who has gone quiet for a long time.

    See `DecisionEngineService.clientes_dormidos` for the exact definition
    and threshold. `ultimo_contrato` is the client's most recently started
    `Pauta` (same pick as `AnalyticsService._contrato_de_referencia`'s
    fallback for a fully-expired client), shown so the reactivation
    conversation has something concrete to reference.
    """

    cliente: Client
    dias_sin_actividad: int
    ultimo_contrato: Pauta


class PatronComercialTipo(StrEnum):
    """Which buying pattern a `OportunidadComercial` is flagging."""

    CONSUMO_ALTO = "consumo_alto"
    NUNCA_PREMIUM = "nunca_premium"
    RECURRENCIA_MENSUAL = "recurrencia_mensual"
    RACHA_RENOVACIONES = "racha_renovaciones"
    TIPO_HABITUAL = "tipo_habitual"


@dataclass(frozen=True, slots=True, kw_only=True)
class OportunidadComercial:
    """A pattern-based upsell/renewal cue detected from a `Client`'s own Pauta history.

    The optional fields are populated only for the `tipo` they describe
    (`racha` for `RACHA_RENOVACIONES`, `tipo_habitual` for `TIPO_HABITUAL`,
    `porcentaje_consumido` for `CONSUMO_ALTO`) — always `None` otherwise,
    since each pattern's own `mensaje` already carries the human-readable
    version and the frontend has no need to reconstruct it.
    """

    cliente: Client
    tipo: PatronComercialTipo
    mensaje: str
    racha: int | None = None
    tipo_habitual: PautaTipo | None = None
    porcentaje_consumido: Decimal | None = None
