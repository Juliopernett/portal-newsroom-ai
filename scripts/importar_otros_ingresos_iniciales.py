"""One-time import of Portal Vallenato's historical otros_ingresos spreadsheet.

Same reasoning `scripts/importar_gastos_iniciales.py` already documents: the
data file (`scripts/data/otros_ingresos_historicos.json`, the operator's own
"FACEBOOK" payout tracking — origen/fecha de cobro/valor, enero a julio
2026) is the operator's real business data, not something that belongs in
git history — pass it via `--file -` on stdin instead:

    Get-Content -Raw otros_ingresos_historicos.json | railway ssh --service ... -- \
        python -m scripts.importar_otros_ingresos_iniciales --file -

Each row maps straight onto `core.entities.otro_ingreso.OtroIngreso` — no
transformation needed, same as the Gastos import.

Usage:
    python -m scripts.importar_otros_ingresos_iniciales --file path/to/datos.json
    python -m scripts.importar_otros_ingresos_iniciales --file -   # lee stdin
    python -m scripts.importar_otros_ingresos_iniciales --file datos.json --force
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

from core.entities.otro_ingreso import OtroIngreso
from core.ports.unit_of_work import UnitOfWork
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ImportSummary:
    """What `importar()` actually did, for the operator to sanity-check."""

    ingresos_creados: int = 0


def importar(rows: list[dict[str, Any]], uow: UnitOfWork) -> ImportSummary:
    """Persist `rows` (as loaded from the JSON data file) through `uow`."""
    summary = ImportSummary()
    for row in rows:
        ingreso = OtroIngreso(
            origen=row["origen"],
            monto=Decimal(row["monto"]),
            monto_usd=Decimal(row["monto_usd"]) if row.get("monto_usd") else None,
            fecha_cobro=date.fromisoformat(row["fecha_cobro"]),
        )
        uow.otros_ingresos.save(ingreso)
        summary.ingresos_creados += 1
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        required=True,
        help="Ruta al JSON con los otros_ingresos históricos, o '-' para leerlo de stdin.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Importar aunque ya existan OtroIngreso en la base de datos "
            "(por defecto se aborta para no duplicar)."
        ),
    )
    args = parser.parse_args()

    raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    rows = json.loads(raw)

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        if uow.otros_ingresos.list_all() and not args.force:
            print(
                "Ya existen OtroIngreso en la base de datos — abortando para no duplicar. "
                "Usa --force si de verdad quieres importar de todos modos.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        summary = importar(rows, uow)
        uow.commit()

    logger.info("Importación completa: %d ingresos creados.", summary.ingresos_creados)


if __name__ == "__main__":
    main()
