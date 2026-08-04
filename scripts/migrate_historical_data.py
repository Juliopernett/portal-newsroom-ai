"""One-time import of Portal Vallenato's historical pautas spreadsheet.

Source: `scripts/data/pautas_historicas.json` (103 rows extracted from the
operator's own tracking spreadsheet, 2026-08-03). Decisions made with the
user before writing this, none of them derivable from the data itself:

- `Client.telefono` (required, absent from the spreadsheet) — every
  migrated client gets the placeholder `"Sin dato"`, filled in later by
  hand as real numbers become known.
- `Client.tipo` (required, absent from the spreadsheet) — every migrated
  client defaults to `ClientType.ARTISTA`. Purely a UI label, not read by
  any domain rule (see `core.entities.client`), so a uniform default is
  low-risk and freely correctable per-client afterwards.
- `Pauta.fecha_pago` (required, absent from the spreadsheet) — set equal
  to `fecha_inicio`, the most reasonable assumption without more data.
- ~20 rows are single-post/loose payments with no real client name ("1
  POST".."8 POST", "22 POST", "Un Post", "Dos Post", "Pago Sin
  Identificar") — all merged into one bucket client, `"Cliente Final"`,
  rather than kept as literal one-off client names.
- Two name pairs are the same person written inconsistently ("Andres
  Ariza"/"Andrés Ariza", "Fer Bustillios"/"Fer Bustillos") — merged into
  one client each.
- ~23 rows have the same date in "Desde" and "Hasta" — legitimate
  same-day, one-or-two-post purchases, not a data error (confirmed with
  the user). `Pauta` requires `fecha_fin > fecha_inicio`, so these get
  `fecha_fin = fecha_inicio + 1 day`.

`Pauta` never stores how much of its quota is consumed — that's always
computed from linked `PublicationRequest` history (see
`core.services.pauta_service.PautaService`). So the spreadsheet's
"publicadas" column is reproduced here as that many real `PublicationRequest`
rows in `PUBLICADA` state, not a number — otherwise `publicaciones_restantes`
would be wrong for every migrated Pauta from day one.

The data file itself (client names, contracted amounts) is deliberately
NOT committed to this repository — it's the operator's real business
data, not something that belongs in git history. `--file -` reads it
from stdin instead, so it can be piped in at run time:

    Get-Content -Raw pautas_historicas.json | railway ssh --service ... -- \
        python -m scripts.migrate_historical_data --file -

Usage:
    python -m scripts.migrate_historical_data --file path/to/datos.json
    python -m scripts.migrate_historical_data --file -   # lee stdin
    python -m scripts.migrate_historical_data --file datos.json --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.ports.unit_of_work import UnitOfWork
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from shared.logger import get_logger

logger = get_logger(__name__)

_TELEFONO_PLACEHOLDER = "Sin dato"
_TIPO_DEFAULT = ClientType.ARTISTA
_CLIENTE_FINAL = "Cliente Final"

_NOMBRES_ANONIMOS = {"un post", "dos post", "pago sin identificar"}
_PATRON_N_POST = re.compile(r"\d+\s*post")

_ALIAS = {
    "andres ariza": "Andrés Ariza",
    "fer bustillios": "Fer Bustillos",
}

_TEXTO_HISTORICO = (
    "Publicación histórica migrada desde la planilla de Portal Vallenato "
    "— texto original no disponible."
)


def _canonical_name(raw: str) -> str:
    """Map a raw spreadsheet "Cliente" value to the name its Client gets."""
    key = raw.strip().lower()
    if key in _NOMBRES_ANONIMOS or _PATRON_N_POST.fullmatch(key):
        return _CLIENTE_FINAL
    return _ALIAS.get(key, raw.strip())


@dataclass
class MigrationSummary:
    """What `migrate()` actually did, for the operator to sanity-check."""

    clientes_creados: int = 0
    pautas_creadas: int = 0
    publicaciones_historicas_creadas: int = 0


def migrate(rows: list[dict[str, Any]], uow: UnitOfWork) -> MigrationSummary:
    """Persist `rows` (as loaded from the JSON data file) through `uow`."""
    summary = MigrationSummary()
    clientes_por_nombre: dict[str, Client] = {c.nombre: c for c in uow.clients.list_all()}

    for row in rows:
        nombre = _canonical_name(row["cliente"])
        client = clientes_por_nombre.get(nombre)
        if client is None:
            client = Client(nombre=nombre, tipo=_TIPO_DEFAULT, telefono=_TELEFONO_PLACEHOLDER)
            uow.clients.save(client)
            clientes_por_nombre[nombre] = client
            summary.clientes_creados += 1

        fecha_inicio = date.fromisoformat(row["desde"])
        fecha_fin = date.fromisoformat(row["hasta"])
        if fecha_fin <= fecha_inicio:
            fecha_fin = fecha_inicio + timedelta(days=1)

        pauta = Pauta(
            client_id=client.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            publicaciones_contratadas=row["contratados"],
            valor_pagado=Decimal(row["precio"]),
            fecha_pago=fecha_inicio,
        )
        uow.pautas.save(pauta)
        summary.pautas_creadas += 1

        fecha_recepcion = datetime.combine(fecha_inicio, datetime.min.time(), tzinfo=UTC)
        for _ in range(row["publicadas"]):
            solicitud = PublicationRequest(
                pauta_id=pauta.id,
                texto=_TEXTO_HISTORICO,
                estado=PublicationRequestStatus.PUBLICADA,
                fecha_recepcion=fecha_recepcion,
            )
            uow.publication_requests.save(solicitud)
            summary.publicaciones_historicas_creadas += 1

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        required=True,
        help="Ruta al JSON con las pautas históricas, o '-' para leerlo de stdin.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Migrar aunque ya existan Pautas en la base de datos "
            "(por defecto se aborta para no duplicar)."
        ),
    )
    args = parser.parse_args()

    raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    rows = json.loads(raw)

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        if uow.pautas.list_all() and not args.force:
            print(
                "Ya existen Pautas en la base de datos — abortando para no duplicar. "
                "Usa --force si de verdad quieres migrar de todos modos.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        summary = migrate(rows, uow)
        uow.commit()

    logger.info(
        "Migración completa: %d clientes nuevos, %d pautas, %d publicaciones históricas.",
        summary.clientes_creados,
        summary.pautas_creadas,
        summary.publicaciones_historicas_creadas,
    )


if __name__ == "__main__":
    main()
