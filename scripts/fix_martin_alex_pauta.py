"""One-time data correction: reassign a specific historical Pauta.

The user flagged (2026-08-05) that one Pauta migrated from the
spreadsheet — 2026-07-29 a 2026-08-29, $280.000, 8 contratadas — was
attributed to "Martín Elias Jr" but actually belongs to "Alex Martínez"
(a data-entry mix-up between two similarly-named clients in the source
spreadsheet, not a bug in the migration script itself — see
scripts/migrate_historical_data.py, which only reproduced what the
spreadsheet said).

Safe by default: with no flags, only looks up and prints what it would
change, without touching the database. Aborts loudly (no partial
change) if it doesn't find exactly one client on each side and exactly
one matching Pauta — this is a scalpel for one specific row, not a
general "rename client" tool.

Usage:
    python -m scripts.fix_martin_alex_pauta            # solo lectura
    python -m scripts.fix_martin_alex_pauta --apply     # aplica el cambio
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
from decimal import Decimal

from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork

_ORIGEN = "Martín Elias Jr"
_DESTINO = "Alex Martínez"
_FECHA_INICIO = date(2026, 7, 29)
_FECHA_FIN = date(2026, 8, 29)
_VALOR_PAGADO = Decimal("280000")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar el cambio (por defecto solo muestra qué haría, sin modificar nada).",
    )
    args = parser.parse_args()

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        clientes = uow.clients.list_all()
        origen = [c for c in clientes if c.nombre == _ORIGEN]
        destino = [c for c in clientes if c.nombre == _DESTINO]
        if len(origen) != 1:
            raise SystemExit(f"Esperaba 1 cliente '{_ORIGEN}', encontré {len(origen)}. Abortando.")
        if len(destino) != 1:
            raise SystemExit(
                f"Esperaba 1 cliente '{_DESTINO}', encontré {len(destino)}. Abortando."
            )

        pautas = uow.pautas.list_all()
        candidatas = [
            p
            for p in pautas
            if p.client_id == origen[0].id
            and p.fecha_inicio == _FECHA_INICIO
            and p.fecha_fin == _FECHA_FIN
            and p.valor_pagado == _VALOR_PAGADO
        ]
        if len(candidatas) != 1:
            raise SystemExit(
                f"Esperaba 1 pauta coincidente, encontré {len(candidatas)}. Abortando."
            )

        pauta = candidatas[0]
        print(f"Pauta {pauta.id}: '{_ORIGEN}' -> '{_DESTINO}'")
        print(
            f"  {pauta.fecha_inicio} a {pauta.fecha_fin}, "
            f"${pauta.valor_pagado}, {pauta.publicaciones_contratadas} contratadas"
        )

        if not args.apply:
            print("\n(solo lectura -- corre de nuevo con --apply para aplicar el cambio)")
            return

        actualizada = replace(pauta, client_id=destino[0].id)
        uow.pautas.save(actualizada)
        uow.commit()
        print("Corregido.")


if __name__ == "__main__":
    main()
