"""Domain service: Sprint 5A Decision Analytics — recommendations, not just numbers.

`AnalyticsService` reports facts (counts, rankings, lists) computed purely
from the domain's own rules. `DecisionEngineService` is a different kind of
service built on top of it: it scores, prioritizes and writes the Spanish
copy the commercial team should act on today. Every threshold defined here
(inactivity windows, the health-score weights, the renewal-chain gap) is a
Sprint 5A calibration, not a derived business rule — explicitly expected to
be retuned once the business has used this against real outcomes, unlike
the facts `AnalyticsService` reports.

Wraps an internal `AnalyticsService` built from the same snapshot, the same
way `AnalyticsService` itself wraps a `PautaService` — reused for every
report it already computes (cupo agotado, por vencer, premium, solicitudes
antiguas) rather than recomputed here.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from core.analytics.analytics_service import AnalyticsService
from core.clock import now_local
from core.analytics.decision_view_models import (
    AccionSugerida,
    AlertaInteligente,
    AlertaSeveridad,
    AlertaTipo,
    ClienteDormido,
    ClienteRiesgoAbandono,
    ClienteScoreSalud,
    NivelSalud,
    OportunidadComercial,
    PatronComercialTipo,
)
from core.entities.client import Client
from core.entities.pauta import Pauta, PautaTipo
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.pauta_service import PautaService

_PAQUETES_PREMIUM = frozenset({PautaTipo.SEMESTRAL, PautaTipo.ANUAL})

# Riesgo de Abandono vs. Clientes Dormidos: el primero es "tiene vigencia y
# cupo pagado sin usar, pero no manda nada" (urgente, hay dinero comprometido
# ya sobre la mesa); el segundo es "no tiene nada vigente y lleva mucho sin
# aparecer" (venta nueva, no seguimiento). El umbral de Abandono es más corto
# a propósito — la urgencia de Abandono es mayor, no menor.
_UMBRAL_RIESGO_ABANDONO_DIAS = 15
_UMBRAL_DORMIDO_DIAS = 60

# Gap máximo, en días, entre el fecha_fin de una Pauta de paquete y el
# fecha_inicio de la siguiente para que ambas cuenten como la misma cadena
# de renovaciones (ver `_cadena_actual`). Un gap negativo/solapado (el
# cliente compró el siguiente paquete antes de que venciera el actual)
# siempre cuenta como continuación.
_UMBRAL_GAP_RENOVACION_DIAS = 15

_UMBRAL_CONSUMO_ALTO = Decimal("0.9")
_RACHA_MINIMA_OPORTUNIDAD = 3
_RECURRENCIA_MENSUAL_MINIMA = 3

# Centro de Alertas: ventana de "hace N días no publica" — deliberadamente
# corta y sin solaparse con Riesgo de Abandono (>=15 días), que es la misma
# señal (`_dias_sin_actividad`) leída con más urgencia una vez pasa ese punto.
_UMBRAL_NO_PUBLICA_DIAS = 5
_UMBRAL_VENCE_HOY_DIAS = 0
_UMBRAL_VENCE_PRONTO_DIAS = 3
_UMBRAL_MATERIAL_RECIEN_RECIBIDO_HORAS = 24

# Score de Salud — pesos de cada señal (deben sumar 1.00). Ver docstring de
# `score_salud_cliente` para la justificación de cada uno.
_PESO_CUPO_RESTANTE = Decimal("0.25")
_PESO_DIAS_PARA_VENCER = Decimal("0.20")
_PESO_SOLICITUDES_PENDIENTES = Decimal("0.15")
_PESO_RITMO_CONSUMO = Decimal("0.15")
_PESO_RACHA_RENOVACIONES = Decimal("0.15")
_PESO_ACTIVIDAD_RECIENTE = Decimal("0.10")

_HORIZONTE_DIAS_PARA_VENCER = 30
_RACHA_TOPE_SCORE = 4
_ACTIVIDAD_RECIENTE_DIAS_SANO = 7
_ACTIVIDAD_RECIENTE_DIAS_CRITICO = 30

# Cortes de `NivelSalud` — arbitrarios/ajustables, ver docstring de la clase.
_NIVEL_SALUD_CORTES: list[tuple[int, NivelSalud]] = [
    (85, NivelSalud.EXCELENTE),
    (70, NivelSalud.BUENO),
    (50, NivelSalud.REGULAR),
    (30, NivelSalud.RIESGO),
]
_ESTRELLAS_POR_NIVEL: dict[NivelSalud, int] = {
    NivelSalud.EXCELENTE: 5,
    NivelSalud.BUENO: 4,
    NivelSalud.REGULAR: 3,
    NivelSalud.RIESGO: 2,
    NivelSalud.CRITICO: 1,
}

# Orden de categoría dentro de `centro_alertas`, usado solo para desempatar
# entre alertas de la misma severidad — no reordena dentro de una misma
# categoría (el sort final es estable y cada categoría ya inserta sus
# propios items en el orden correcto: por_vencer por fecha_fin ascendente,
# riesgo_abandono por dias_sin_actividad descendente, etc.).
_ORDEN_TIPO: dict[AlertaTipo, int] = {
    AlertaTipo.CUPO_AGOTADO: 0,
    AlertaTipo.POR_VENCER: 1,
    AlertaTipo.MENOS_DE_N_RESTANTES: 2,
    AlertaTipo.SIN_ACTIVIDAD_RECIENTE: 3,
    AlertaTipo.MATERIAL_RECIBIDO: 4,
    AlertaTipo.RIESGO_ABANDONO: 5,
    AlertaTipo.SOLICITUD_ANTIGUA: 6,
}


def _clamp01(valor: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), valor))


class DecisionEngineService:
    """Computes prioritized, actionable recommendations from a fixed snapshot of domain data."""

    def __init__(
        self,
        clients: Sequence[Client],
        pautas: Sequence[Pauta],
        solicitudes: Sequence[PublicationRequest],
        clock: Callable[[], datetime] = lambda: now_local(),
    ) -> None:
        """`clock` is injectable so tests can control what "now" means.

        Builds one internal `AnalyticsService` from the same snapshot and
        `clock` rather than accepting one from outside — same reasoning
        `AnalyticsService` itself gives for owning its `PautaService`: a
        single knob for "now" instead of two independently-injectable
        clocks that could disagree in tests.
        """
        self._clients = clients
        self._pautas = pautas
        self._solicitudes = solicitudes
        self._clock = clock
        self._analytics = AnalyticsService(clients, pautas, solicitudes, clock=clock)
        self._pauta_service = PautaService(clock=lambda: clock().date())

    # ---------- Última actividad / Riesgo de Abandono / Dormidos ----------

    def clientes_riesgo_abandono(
        self, umbral_dias: int = _UMBRAL_RIESGO_ABANDONO_DIAS
    ) -> list[ClienteRiesgoAbandono]:
        """Return `Client`s with a vigente, unexhausted Pauta who have gone quiet.

        "Riesgo de Abandono" means there is money and quota already
        committed (`publicaciones_restantes > 0` on the contrato de
        referencia) that the client simply isn't using — distinct from
        `clientes_dormidos`, which requires *no* vigente Pauta at all.
        Sorted by `dias_sin_actividad` descending — the longest silences
        first.
        """
        resultado = []
        for cliente in self._clients:
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            contrato = self._contrato_de_referencia(pautas_cliente)
            if not self._pauta_service.esta_vigente(contrato):
                continue
            restantes = self._pauta_service.publicaciones_restantes(contrato, self._solicitudes)
            if restantes <= 0:
                continue
            dias = self._dias_sin_actividad(cliente.id)
            if dias < umbral_dias:
                continue
            resultado.append(
                ClienteRiesgoAbandono(
                    cliente=cliente,
                    dias_sin_actividad=dias,
                    publicaciones_restantes=restantes,
                    fecha_vencimiento=contrato.fecha_fin,
                )
            )
        resultado.sort(key=lambda item: item.dias_sin_actividad, reverse=True)
        return resultado

    def clientes_dormidos(self, umbral_dias: int = _UMBRAL_DORMIDO_DIAS) -> list[ClienteDormido]:
        """Return `Client`s with no vigente Pauta who have gone quiet for a long time.

        Scoped to clients with at least one Pauta — a `Client` who never
        contracted anything has no stored timestamp at all (`Client` has
        no `fecha_creacion`), so "how long have they been dormant" isn't
        computable for them; out of scope for Sprint 5A (confirmed with
        the business), not silently guessed at.
        """
        resultado = []
        for cliente in self._clients:
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            contrato = self._contrato_de_referencia(pautas_cliente)
            if self._pauta_service.esta_vigente(contrato):
                continue
            dias = self._dias_sin_actividad(cliente.id)
            if dias < umbral_dias:
                continue
            resultado.append(
                ClienteDormido(cliente=cliente, dias_sin_actividad=dias, ultimo_contrato=contrato)
            )
        resultado.sort(key=lambda item: item.dias_sin_actividad, reverse=True)
        return resultado

    # ---------- Cadena de renovaciones ----------

    def racha_renovaciones(self, client_id: str) -> int:
        """Return how many renewal *transitions* the Client's current chain has.

        "Alex lleva cuatro renovaciones consecutivas" = 4 transitions = 5
        contracts in the chain — a deliberate interpretation (contracts -
        1), adjustable if the business prefers to count contracts instead.
        """
        return max(0, len(self._cadena_actual(client_id)) - 1)

    # ---------- Score de Salud ----------

    def score_salud_cliente(self, client_id: str) -> ClienteScoreSalud | None:
        """Return `client_id`'s health score, or `None` if they have no Pauta at all.

        A weighted sum of 6 signals, each normalized to [0,1] then scaled
        by its weight (weights sum to 1.00, see the `_PESO_*` constants):

        - Cupo restante (25%): `restantes/contratadas` on the contrato de
          referencia; 0 if it isn't vigente. The single biggest signal —
          an exhausted or near-exhausted vigente contract is the clearest
          "needs a renewal conversation now" signal available.
        - Días para vencer (20%): 0 if not vigente/already past fecha_fin;
          1.0 at >=30 days out; linear in between. 30 chosen to match the
          existing "horizonte de renovación" the frontend already uses for
          its 30-day bucket.
        - Solicitudes pendientes (15%): `max(0, 1 - 0.25*n)` — 4+ pending
          requests floors this at 0. A backlog isn't the client's fault,
          but it is a real signal that Portal Vallenato isn't delivering
          on what was sold, which erodes the relationship regardless of
          whose queue it's stuck in.
        - Ritmo de consumo (15%): compares how much of the contract's
          quota is used against how much of its calendar duration has
          elapsed. A vigente client who has barely published despite the
          contract being half over may be losing interest even though
          nothing else looks urgent yet.
        - Racha de renovaciones / lealtad (15%): `min(racha, 4)/4` — a
          first-time client scores 0 here, which is "no history yet", not
          a penalty.
        - Actividad reciente (10%): 1.0 at <=7 days since last activity,
          0.0 at >=30, linear in between.

        Only computed for a Client with >=1 Pauta — same exclusion
        `AnalyticsService.ranking_comercial` uses, there is nothing to
        score otherwise.
        """
        pautas_cliente = self._pautas_de(client_id)
        if not pautas_cliente:
            return None
        cliente = self._cliente_de(client_id)
        if cliente is None:
            return None

        contrato = self._contrato_de_referencia(pautas_cliente)
        vigente = self._pauta_service.esta_vigente(contrato)
        hoy = self._clock().date()

        señales = [
            (self._senal_cupo_restante(contrato, vigente), _PESO_CUPO_RESTANTE),
            (self._senal_dias_para_vencer(contrato, vigente, hoy), _PESO_DIAS_PARA_VENCER),
            (
                self._senal_solicitudes_pendientes(client_id),
                _PESO_SOLICITUDES_PENDIENTES,
            ),
            (self._senal_ritmo_consumo(contrato, vigente, hoy), _PESO_RITMO_CONSUMO),
            (self._senal_racha_renovaciones(client_id), _PESO_RACHA_RENOVACIONES),
            (
                self._senal_actividad_reciente(self._dias_sin_actividad(client_id)),
                _PESO_ACTIVIDAD_RECIENTE,
            ),
        ]
        total = sum((valor * peso for valor, peso in señales), start=Decimal("0"))
        score = int((total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        score = max(0, min(100, score))
        nivel = self._nivel_desde_score(score)
        return ClienteScoreSalud(
            cliente=cliente, score=score, estrellas=_ESTRELLAS_POR_NIVEL[nivel], nivel=nivel
        )

    def scores_salud(self) -> list[ClienteScoreSalud]:
        """Return every Client's health score, worst first — the ones needing attention up top."""
        resultado = [
            score
            for score in (self.score_salud_cliente(cliente.id) for cliente in self._clients)
            if score is not None
        ]
        resultado.sort(key=lambda item: item.score)
        return resultado

    # ---------- Oportunidades Comerciales (patrones finos) ----------

    def clientes_consumo_alto(self) -> list[OportunidadComercial]:
        """Return Clients whose vigente contrato de referencia is >=90% consumed (but not 100%).

        Deliberately distinct from `AnalyticsService`'s
        `_CUPO_BAJO_UMBRAL` (20% *remaining* → operational alert): this is
        a stricter, upsell-framed threshold ("about to need more"), not
        an alert about running out. Excludes fully exhausted contracts —
        those are already `clientes_con_cupo_agotado`, a more urgent
        operational alert, not an upsell cue.
        """
        resultado = []
        for cliente in self._clients:
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            contrato = self._contrato_de_referencia(pautas_cliente)
            if not self._pauta_service.esta_vigente(contrato):
                continue
            consumidas = self._pauta_service.publicaciones_consumidas(contrato, self._solicitudes)
            proporcion = Decimal(consumidas) / Decimal(contrato.publicaciones_contratadas)
            if not (_UMBRAL_CONSUMO_ALTO <= proporcion < Decimal("1")):
                continue
            porcentaje = (proporcion * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            resultado.append(
                OportunidadComercial(
                    cliente=cliente,
                    tipo=PatronComercialTipo.CONSUMO_ALTO,
                    mensaje=f"{cliente.nombre} ya consumió el {porcentaje}% de su plan actual.",
                    porcentaje_consumido=proporcion * 100,
                )
            )
        return resultado

    def clientes_nunca_premium(self) -> list[OportunidadComercial]:
        """Return Clients who have never contracted a Semestral or Anual Pauta, ever.

        Historical, across every Pauta the client has ever had — unlike
        `AnalyticsService.clientes_premium`, which only looks at the
        vigente one.
        """
        resultado = []
        for cliente in self._clients:
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            if any(p.tipo in _PAQUETES_PREMIUM for p in pautas_cliente):
                continue
            resultado.append(
                OportunidadComercial(
                    cliente=cliente,
                    tipo=PatronComercialTipo.NUNCA_PREMIUM,
                    mensaje=f"{cliente.nombre} nunca ha contratado un plan semestral o anual.",
                )
            )
        return resultado

    def clientes_recurrencia_mensual(self) -> list[OportunidadComercial]:
        """Return Clients whose current renewal chain is >=3 consecutive Mensual Pautas."""
        resultado = []
        for cliente in self._clients:
            cadena = self._cadena_actual(cliente.id)
            if len(cadena) < _RECURRENCIA_MENSUAL_MINIMA:
                continue
            if not all(p.tipo is PautaTipo.MENSUAL for p in cadena):
                continue
            resultado.append(
                OportunidadComercial(
                    cliente=cliente,
                    tipo=PatronComercialTipo.RECURRENCIA_MENSUAL,
                    mensaje=f"{cliente.nombre} compra un plan mensual de forma recurrente.",
                )
            )
        return resultado

    def clientes_racha_renovaciones(
        self, minimo: int = _RACHA_MINIMA_OPORTUNIDAD
    ) -> list[OportunidadComercial]:
        """Return Clients with `racha_renovaciones` at or above `minimo`."""
        resultado = []
        for cliente in self._clients:
            racha = self.racha_renovaciones(cliente.id)
            if racha < minimo:
                continue
            resultado.append(
                OportunidadComercial(
                    cliente=cliente,
                    tipo=PatronComercialTipo.RACHA_RENOVACIONES,
                    mensaje=f"{cliente.nombre} lleva {racha} renovaciones consecutivas.",
                    racha=racha,
                )
            )
        return resultado

    def clientes_tipo_habitual(self) -> list[OportunidadComercial]:
        """Return Clients whose non-Individual Pautas have a strict-majority `PautaTipo`.

        Requires at least 2 package-type Pautas and that the most common
        `tipo` among them is a strict majority (`frecuencia*2 >
        len(tipos)`) — a client with a genuine tie (e.g. 2 Mensual, 2
        Trimestral) has no "habitual" type, so is excluded rather than
        arbitrarily picking one.
        """
        resultado = []
        for cliente in self._clients:
            tipos = [
                p.tipo for p in self._pautas_de(cliente.id) if p.tipo is not PautaTipo.INDIVIDUAL
            ]
            if len(tipos) < 2:
                continue
            tipo_top, frecuencia = Counter(tipos).most_common(1)[0]
            if frecuencia * 2 <= len(tipos):
                continue
            resultado.append(
                OportunidadComercial(
                    cliente=cliente,
                    tipo=PatronComercialTipo.TIPO_HABITUAL,
                    mensaje=f"{cliente.nombre} suele comprar paquetes {tipo_top.value}.",
                    tipo_habitual=tipo_top,
                )
            )
        return resultado

    def oportunidades_comerciales(self) -> list[OportunidadComercial]:
        """Return every fine-grained buying-pattern opportunity, grouped by pattern type."""
        return [
            *self.clientes_consumo_alto(),
            *self.clientes_nunca_premium(),
            *self.clientes_recurrencia_mensual(),
            *self.clientes_racha_renovaciones(),
            *self.clientes_tipo_habitual(),
        ]

    # ---------- Centro de Alertas Inteligentes ----------

    def centro_alertas(self) -> list[AlertaInteligente]:
        """Return one prioritized, already-written task list combining every signal below.

        Consolidates, in severity order: cupo agotado, por vencer (con
        sub-umbrales hoy/<=3 días/<=7 días), menos de 3 restantes, "hace N
        días no publica" (nuevo — ventana 5-14 días, ver
        `_UMBRAL_NO_PUBLICA_DIAS`), "ya envió material" (nuevo, últimas
        24h), riesgo de abandono (nuevo, >=15 días) y solicitudes
        antiguas. Un Client ya cubierto por una categoría más severa no se
        repite en "menos de 3 restantes" ni en "hace N días no publica" —
        cada uno aparece una sola vez con su señal más urgente.
        """
        alertas: list[AlertaInteligente] = []
        ids_cubiertos: set[str] = set()

        for cliente in self._analytics.clientes_con_cupo_agotado():
            ids_cubiertos.add(cliente.id)
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.CUPO_AGOTADO,
                    severidad=AlertaSeveridad.CRITICA,
                    mensaje=f"{cliente.nombre}: cupo agotado, necesita renovación.",
                    cliente=cliente,
                    accion=AccionSugerida.RENOVAR,
                )
            )

        hoy = self._clock().date()
        pautas_por_vencer_ordenadas = sorted(
            self._analytics.pautas_por_vencer(dias=7), key=lambda p: p.fecha_fin
        )
        for pauta in pautas_por_vencer_ordenadas:
            if pauta.tipo is PautaTipo.INDIVIDUAL:
                continue
            cliente = self._cliente_de(pauta.client_id)
            if cliente is None or cliente.id in ids_cubiertos:
                continue
            ids_cubiertos.add(cliente.id)
            dias = (pauta.fecha_fin - hoy).days
            if dias <= _UMBRAL_VENCE_HOY_DIAS:
                mensaje = f"Hoy vence {cliente.nombre}."
                severidad = AlertaSeveridad.CRITICA
            elif dias <= _UMBRAL_VENCE_PRONTO_DIAS:
                mensaje = f"{cliente.nombre} vence en {dias} día{'' if dias == 1 else 's'}."
                severidad = AlertaSeveridad.CRITICA
            else:
                mensaje = f"{cliente.nombre} vence en {dias} días."
                severidad = AlertaSeveridad.ATENCION
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.POR_VENCER,
                    severidad=severidad,
                    mensaje=mensaje,
                    cliente=cliente,
                    accion=AccionSugerida.RENOVAR,
                    dias=dias,
                )
            )

        for cliente in self._analytics.clientes_con_menos_de_n_publicaciones_restantes(minimo=3):
            if cliente.id in ids_cubiertos:
                continue
            ids_cubiertos.add(cliente.id)
            contrato = self._contrato_de_referencia(self._pautas_de(cliente.id))
            restantes = self._pauta_service.publicaciones_restantes(contrato, self._solicitudes)
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.MENOS_DE_N_RESTANTES,
                    severidad=AlertaSeveridad.ATENCION,
                    mensaje=f"{cliente.nombre}: solo quedan {restantes} publicaciones.",
                    cliente=cliente,
                    accion=AccionSugerida.VER_CLIENTE,
                )
            )

        for cliente in self._clients:
            if cliente.id in ids_cubiertos:
                continue
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            contrato = self._contrato_de_referencia(pautas_cliente)
            if not self._pauta_service.esta_vigente(contrato):
                continue
            dias_inactivo = self._dias_sin_actividad(cliente.id)
            if not (_UMBRAL_NO_PUBLICA_DIAS <= dias_inactivo < _UMBRAL_RIESGO_ABANDONO_DIAS):
                continue
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.SIN_ACTIVIDAD_RECIENTE,
                    severidad=AlertaSeveridad.ATENCION,
                    mensaje=f"Hace {dias_inactivo} días {cliente.nombre} no publica.",
                    cliente=cliente,
                    accion=AccionSugerida.VER_CLIENTE,
                    dias=dias_inactivo,
                )
            )

        limite_material = self._clock() - timedelta(hours=_UMBRAL_MATERIAL_RECIEN_RECIBIDO_HORAS)
        pautas_por_id = {p.id: p for p in self._pautas}
        for solicitud in self._solicitudes:
            if solicitud.estado != PublicationRequestStatus.RECIBIDA:
                continue
            if solicitud.fecha_recepcion < limite_material:
                continue
            pauta = pautas_por_id.get(solicitud.pauta_id) if solicitud.pauta_id else None
            cliente = self._cliente_de(pauta.client_id) if pauta is not None else None
            if cliente is None:
                continue
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.MATERIAL_RECIBIDO,
                    severidad=AlertaSeveridad.INFORMATIVA,
                    mensaje=f"{cliente.nombre} ya envió material nuevo.",
                    cliente=cliente,
                    accion=AccionSugerida.VER_SOLICITUDES,
                )
            )

        for riesgo in self.clientes_riesgo_abandono():
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.RIESGO_ABANDONO,
                    severidad=AlertaSeveridad.CRITICA,
                    mensaje=(
                        f"{riesgo.cliente.nombre}: hace {riesgo.dias_sin_actividad} días no "
                        f"envía material. Tiene {riesgo.publicaciones_restantes} "
                        "publicaciones disponibles."
                    ),
                    cliente=riesgo.cliente,
                    accion=AccionSugerida.CONTACTAR,
                    dias=riesgo.dias_sin_actividad,
                )
            )

        antiguas = self._analytics.solicitudes_antiguas(horas=4)
        if antiguas:
            n = len(antiguas)
            alertas.append(
                AlertaInteligente(
                    tipo=AlertaTipo.SOLICITUD_ANTIGUA,
                    severidad=AlertaSeveridad.CRITICA,
                    mensaje=(
                        f"{n} solicitud{'' if n == 1 else 'es'} lleva{'' if n == 1 else 'n'} "
                        "más de 4h esperando respuesta."
                    ),
                    cliente=None,
                    accion=AccionSugerida.VER_SOLICITUDES,
                )
            )

        orden_severidad = {
            AlertaSeveridad.CRITICA: 0,
            AlertaSeveridad.ATENCION: 1,
            AlertaSeveridad.INFORMATIVA: 2,
        }
        # Sort estable: dentro de la misma (severidad, tipo) conserva el orden
        # en que cada bloque ya insertó sus items (por_vencer por fecha_fin
        # ascendente, riesgo_abandono por dias_sin_actividad descendente).
        alertas.sort(key=lambda a: (orden_severidad[a.severidad], _ORDEN_TIPO[a.tipo]))
        return alertas

    # ---------- helpers ----------

    def _pautas_de(self, client_id: str) -> list[Pauta]:
        return [p for p in self._pautas if p.client_id == client_id]

    def _cliente_de(self, client_id: str) -> Client | None:
        return next((c for c in self._clients if c.id == client_id), None)

    def _contrato_de_referencia(self, pautas_cliente: Sequence[Pauta]) -> Pauta:
        """Return the Pauta that represents a Client "right now" — same rule as
        `AnalyticsService._contrato_de_referencia` (duplicated rather than reached
        into across services): the vigente Pauta started most recently, or, with
        none vigente, the most recently started one overall.
        """
        vigentes = [p for p in pautas_cliente if self._pauta_service.esta_vigente(p)]
        candidatas = vigentes or pautas_cliente
        return max(candidatas, key=lambda p: p.fecha_inicio)

    def _ultima_actividad(self, client_id: str) -> datetime:
        """Return the most recent timestamp evidencing activity from this Client.

        There is no activity/events table — this is the best approximation
        derivable from existing data: `max` of every linked
        `PublicationRequest.fecha_recepcion` (a request arriving IS
        activity, even if it's never published) and every owned
        `Pauta.fecha_registro` (registering a new Pauta IS activity — it
        means the client just contracted or renewed). A Client with Pautas
        but zero linked solicitudes falls back to `max(fecha_registro)` —
        never `None` for a Client with >=1 Pauta, which every caller
        guarantees before calling this.
        """
        pautas_cliente = self._pautas_de(client_id)
        pauta_ids = {p.id for p in pautas_cliente}
        fechas = [p.fecha_registro for p in pautas_cliente]
        fechas.extend(s.fecha_recepcion for s in self._solicitudes if s.pauta_id in pauta_ids)
        return max(fechas)

    def _dias_sin_actividad(self, client_id: str) -> int:
        dias = (self._clock() - self._ultima_actividad(client_id)).days
        return max(0, dias)

    def _cadena_actual(self, client_id: str) -> list[Pauta]:
        """Return the chain of consecutive package-type Pautas ending in the most recent one.

        Walks the client's non-Individual Pautas backwards from the most
        recently started, stopping at the first gap between one Pauta's
        `fecha_fin` and the next's `fecha_inicio` that exceeds
        `_UMBRAL_GAP_RENOVACION_DIAS` (an overlapping/negative gap always
        counts as continuous). If the Client's single most recent Pauta
        overall is Individual, the current chain is empty — an Individual
        purchase breaks the renewal streak, it doesn't extend it.
        """
        pautas_todas = sorted(self._pautas_de(client_id), key=lambda p: p.fecha_inicio)
        if not pautas_todas or pautas_todas[-1].tipo is PautaTipo.INDIVIDUAL:
            return []
        pautas_paquete = [p for p in pautas_todas if p.tipo is not PautaTipo.INDIVIDUAL]

        cadena = [pautas_paquete[-1]]
        for anterior in reversed(pautas_paquete[:-1]):
            gap_dias = (cadena[0].fecha_inicio - anterior.fecha_fin).days
            if gap_dias > _UMBRAL_GAP_RENOVACION_DIAS:
                break
            cadena.insert(0, anterior)
        return cadena

    def _nivel_desde_score(self, score: int) -> NivelSalud:
        for corte, nivel in _NIVEL_SALUD_CORTES:
            if score >= corte:
                return nivel
        return NivelSalud.CRITICO

    def _senal_cupo_restante(self, contrato: Pauta, vigente: bool) -> Decimal:
        if not vigente:
            return Decimal("0")
        restantes = self._pauta_service.publicaciones_restantes(contrato, self._solicitudes)
        return _clamp01(Decimal(restantes) / Decimal(contrato.publicaciones_contratadas))

    def _senal_dias_para_vencer(self, contrato: Pauta, vigente: bool, hoy: date) -> Decimal:
        if not vigente:
            return Decimal("0")
        dias = (contrato.fecha_fin - hoy).days
        if dias <= 0:
            return Decimal("0")
        if dias >= _HORIZONTE_DIAS_PARA_VENCER:
            return Decimal("1")
        return Decimal(dias) / Decimal(_HORIZONTE_DIAS_PARA_VENCER)

    def _senal_solicitudes_pendientes(self, client_id: str) -> Decimal:
        pauta_ids = {p.id for p in self._pautas_de(client_id)}
        n = sum(
            1
            for s in self._solicitudes
            if s.pauta_id in pauta_ids and s.estado == PublicationRequestStatus.RECIBIDA
        )
        return _clamp01(Decimal("1") - Decimal("0.25") * n)

    def _senal_ritmo_consumo(self, contrato: Pauta, vigente: bool, hoy: date) -> Decimal:
        if not vigente:
            return Decimal("0")
        duracion_total = (contrato.fecha_fin - contrato.fecha_inicio).days
        dias_transcurridos = max(0, min(duracion_total, (hoy - contrato.fecha_inicio).days))
        avance_esperado = Decimal(dias_transcurridos) / Decimal(duracion_total)
        consumidas = self._pauta_service.publicaciones_consumidas(contrato, self._solicitudes)
        avance_real = Decimal(consumidas) / Decimal(contrato.publicaciones_contratadas)
        diferencia = avance_esperado - avance_real
        if diferencia <= 0:
            return Decimal("1")
        return _clamp01(Decimal("1") - 2 * diferencia)

    def _senal_racha_renovaciones(self, client_id: str) -> Decimal:
        racha = self.racha_renovaciones(client_id)
        return _clamp01(Decimal(min(racha, _RACHA_TOPE_SCORE)) / Decimal(_RACHA_TOPE_SCORE))

    def _senal_actividad_reciente(self, dias_sin_actividad: int) -> Decimal:
        if dias_sin_actividad <= _ACTIVIDAD_RECIENTE_DIAS_SANO:
            return Decimal("1")
        if dias_sin_actividad >= _ACTIVIDAD_RECIENTE_DIAS_CRITICO:
            return Decimal("0")
        rango = _ACTIVIDAD_RECIENTE_DIAS_CRITICO - _ACTIVIDAD_RECIENTE_DIAS_SANO
        return Decimal(_ACTIVIDAD_RECIENTE_DIAS_CRITICO - dias_sin_actividad) / Decimal(rango)
