"""Scan the Radar's sources and persist new candidates — the hourly job.

Sprint Fuentes (2026-10-29). A deliberate ops-triggered script (same
reasoning as `scripts/purgar_media_expirados.py`: no scheduler living
inside the web process). Run it from a Railway cron service every hour;
it only scans the sources that are due (each has its own interval), so
firing it often costs almost nothing.

Idempotent: a candidate already stored is counted as a duplicate and
skipped.

Usage:
    python -m scripts.escanear_fuentes            # only sources that are due
    python -m scripts.escanear_fuentes --forzar   # every enabled source now
"""

from __future__ import annotations

import argparse

from agents.radar.fabrica import crear_adaptador
from core.services.source_scan_service import ESTADO_OK, escanear_fuentes
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--forzar", action="store_true", help="Escanear todas las fuentes activas, sin esperar"
    )
    args = parser.parse_args()

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        resultados = escanear_fuentes(uow, crear_adaptador, forzar=args.forzar)

    for r in resultados:
        detalle = (
            r.error or f"{r.consultados} consultados, {r.nuevos} nuevos, {r.duplicados} duplicados"
        )
        print(f"[{r.estado}] {r.fuente}: {detalle}")
    print(f"Nuevos en total: {sum(r.nuevos for r in resultados if r.estado == ESTADO_OK)}")


if __name__ == "__main__":
    main()
