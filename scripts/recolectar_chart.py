"""Collect the Chart Vallenato's daily YouTube view counts — the daily job.

Same shape as `scripts/escanear_fuentes.py`: a deliberate ops-triggered
script, run once a day from a Railway cron service (no scheduler lives inside
the web process). It discovers new uploads of every followed channel and
saves today's total view count of every tracked video. Idempotent within a
day: running it twice only rewrites today's snapshot.

Usage:
    python -m scripts.recolectar_chart
"""

from __future__ import annotations

from agents.youtube.client import YouTubeDataApiReader
from config.settings import get_settings
from core.services.chart_service import recolectar_chart
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork


def main() -> None:
    reader = YouTubeDataApiReader(get_settings())
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        res = recolectar_chart(uow, reader)
        uow.commit()

    print(
        f"Canales ok: {res.canales_ok} | videos nuevos: {res.videos_nuevos} | "
        f"videos seguidos: {res.videos_seguidos} | snapshots: {res.snapshots}"
    )
    for error in res.canales_con_error:
        print(f"[canal con error] {error}")
    if res.error_estadisticas:
        print(f"[estadísticas] {res.error_estadisticas}")


if __name__ == "__main__":
    main()
