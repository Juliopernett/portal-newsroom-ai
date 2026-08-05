"""Business "now" for date-vigency logic (Pauta vigente/vencida, días para
vencer, año actual, horas en espera).

Portal Vallenato operates out of Colombia (UTC-5, no DST). The rest of the
codebase timestamps records in UTC (`created_at`, `fecha_registro`, ...) —
that's the right call for storage. But "is this Pauta still valid today"
is a question about the business's calendar day, not UTC's: `datetime.now(UTC)`
rolls over to the next day 5 hours before local midnight, which quietly
expires same-day/short pautas (and misfires renewal/staleness thresholds)
every evening.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("America/Bogota")


def now_local() -> datetime:
    """Current time in Portal Vallenato's business timezone (Bogotá, UTC-5)."""
    return datetime.now(BUSINESS_TZ)
