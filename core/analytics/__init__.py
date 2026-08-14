"""Analytics: read-only business metrics over the Commercial pillar.

`AnalyticsService` is the only thing meant to be imported from outside this
package — everything it returns is built from `core.entities`/`core.services`
data already available elsewhere in `core/`, never new persisted state.
Re-exported below for ergonomic imports (`from core.analytics import
AnalyticsService`), same convention as `core/services/`.
"""

from __future__ import annotations

from core.analytics.analytics_service import AnalyticsService
from core.analytics.decision_engine import DecisionEngineService
from core.analytics.rentabilidad_service import rentabilidad_mensual
from core.analytics.view_models import ClienteIngreso, ClientePesoComercial, RentabilidadMensualItem

__all__ = [
    "AnalyticsService",
    "ClienteIngreso",
    "ClientePesoComercial",
    "DecisionEngineService",
    "RentabilidadMensualItem",
    "rentabilidad_mensual",
]
