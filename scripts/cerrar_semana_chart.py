"""Close the Chart Vallenato's week — the weekly job.

Run from a Railway cron service every Saturday at 05:00 UTC (= Friday 24:00
Colombia time). It discovers the whole catalog of every followed channel,
measures every video once (the week's *close*) and builds the draft edition
that the editor reviews and publishes from the panel.

Exits with status 1 when anything failed (a channel, or the statistics call),
so Railway marks the run as failed and the problem is not silent.

Usage:
    python -m scripts.cerrar_semana_chart
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from agents.youtube.client import YouTubeDataApiReader
from config.settings import get_settings
from core.services.chart_semanal_service import cerrar_semana
from core.services.chart_service import purgar_datos_antiguos
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork


def main() -> int:
    settings = get_settings()
    reader = YouTubeDataApiReader(settings)
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        res = cerrar_semana(uow, reader)
        limpieza = purgar_datos_antiguos(
            uow, datetime.now(UTC).date(), settings.chart_retencion_dias
        )
        uow.commit()

    edicion = f"borrador con {res.edicion_filas} filas" if res.edicion_generada else "no generada"
    print(
        f"Semana {res.semana_fin} | canales ok: {res.canales_ok} | "
        f"videos nuevos: {res.videos_nuevos} | medidos: {res.videos_medidos} | "
        f"edición: {edicion} | sin base: {res.sin_base} | "
        f"retirados (ya no en YouTube): {res.videos_retirados}"
    )
    print(
        f"Limpieza (>{settings.chart_retencion_dias} días): {limpieza.snapshots} snapshots, "
        f"{limpieza.cortes} cierres, {limpieza.ediciones} ediciones"
    )
    if res.nota:
        print(res.nota)
    for error in res.canales_con_error:
        print(f"[canal con error] {error}")
    if res.error_estadisticas:
        print(f"[estadísticas] {res.error_estadisticas}")
    return 1 if res.hubo_errores else 0


if __name__ == "__main__":
    sys.exit(main())
