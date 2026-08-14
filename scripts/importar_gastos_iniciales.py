"""One-time import of Portal Vallenato's historical gastos spreadsheet.

Source: `scripts/data/gastos_historicos.json` (30 rows from the operator's
own "GASTOS PORTAL VALLENATO" tracking sheet, pasted 2026-08-14 — pagos
mensuales a Antonio y Andrés, hosting, Meta Verified, Cámara de Comercio,
dominio, enero a julio 2026). Same reasoning
`scripts/migrate_historical_data.py` already documents for not committing
the data file: it's the operator's real business data, not something that
belongs in git history. `--file -` reads it from stdin instead, so it can
be piped in at run time:

    Get-Content -Raw gastos_historicos.json | railway ssh --service ... -- \
        python -m scripts.importar_gastos_iniciales --file -

Each row maps straight onto `core.entities.gasto.Gasto` — no
transformation needed, unlike `migrate_historical_data.py`'s pautas
(no client to resolve, no derived dates).

Usage:
    python -m scripts.importar_gastos_iniciales --file path/to/datos.json
    python -m scripts.importar_gastos_iniciales --file -   # lee stdin
    python -m scripts.importar_gastos_iniciales --file datos.json --force
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.entities.gasto import Gasto
from core.ports.unit_of_work import UnitOfWork
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ImportSummary:
    """What `importar()` actually did, for the operator to sanity-check."""

    gastos_creados: int = 0


def importar(rows: list[dict[str, Any]], uow: UnitOfWork) -> ImportSummary:
    """Persist `rows` (as loaded from the JSON data file) through `uow`."""
    summary = ImportSummary()
    for row in rows:
        gasto = Gasto(
            descripcion=row["descripcion"],
            valor=Decimal(row["valor"]),
            fecha=date.fromisoformat(row["fecha"]),
        )
        uow.gastos.save(gasto)
        summary.gastos_creados += 1
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        required=True,
        help="Ruta al JSON con los gastos históricos, o '-' para leerlo de stdin.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Importar aunque ya existan Gastos en la base de datos "
            "(por defecto se aborta para no duplicar)."
        ),
    )
    args = parser.parse_args()

    raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    rows = json.loads(raw)

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        if uow.gastos.list_all() and not args.force:
            print(
                "Ya existen Gastos en la base de datos — abortando para no duplicar. "
                "Usa --force si de verdad quieres importar de todos modos.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        summary = importar(rows, uow)
        uow.commit()

    logger.info("Importación completa: %d gastos creados.", summary.gastos_creados)


if __name__ == "__main__":
    main()
