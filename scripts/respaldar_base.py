"""Nightly backup of the Postgres database to an S3-compatible bucket (R2).

Run from a Railway cron service (e.g. `0 8 * * *` UTC = 03:00 Colombia):

    python -m scripts.respaldar_base

It runs `pg_dump` (custom format, already compressed), uploads the file to the
bucket, checks the stored size matches, and keeps the most recent
`RESPALDO_CONSERVAR` copies (30 by default). Exits 1 on any failure so Railway
flags the run and emails the owner. The database password goes through the
`PGPASSWORD` environment variable, never the command line.

To restore into an EMPTY database (see docs/RESPALDOS.md):

    pg_restore --no-owner --no-privileges --dbname "$DATABASE_URL" respaldo.dump
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.engine import make_url

from agents.storage.respaldo_s3 import AlmacenRespaldosS3, RespaldoNoConfigurado
from config.settings import get_settings
from core.ports.almacen_respaldos import AlmacenRespaldoError
from core.services.respaldo_service import ejecutar_respaldo

_TIMEOUT_SEGUNDOS = 1800


def comando_pg_dump(url_base: str, destino: Path) -> tuple[list[str], dict[str, str]]:
    """`pg_dump` argv and environment for `url_base` (the password only in the env)."""
    url = make_url(url_base)
    if not url.drivername.startswith("postgresql"):
        raise AlmacenRespaldoError("El respaldo solo está implementado para Postgres.")
    comando = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 5432}",
        f"--username={url.username or 'postgres'}",
        f"--dbname={url.database or 'postgres'}",
        f"--file={destino}",
    ]
    return comando, {**os.environ, "PGPASSWORD": url.password or ""}


def _volcador(url_base: str) -> Callable[[Path], None]:
    def volcar(destino: Path) -> None:
        comando, entorno = comando_pg_dump(url_base, destino)
        try:
            resultado = subprocess.run(  # noqa: S603 - fixed argv, no shell
                comando, env=entorno, capture_output=True, text=True, timeout=_TIMEOUT_SEGUNDOS
            )
        except FileNotFoundError:
            raise AlmacenRespaldoError("pg_dump no está instalado en esta imagen.") from None
        if resultado.returncode != 0:
            # pg_dump's own message (it never prints the password) is the useful part.
            raise AlmacenRespaldoError(f"pg_dump falló: {resultado.stderr.strip()[:400]}")

    return volcar


def main() -> int:
    settings = get_settings()
    try:
        almacen = AlmacenRespaldosS3(settings)
        res = ejecutar_respaldo(
            _volcador(settings.database_url),
            almacen,
            prefijo=settings.respaldo_prefijo,
            conservar=settings.respaldo_conservar,
        )
    except (RespaldoNoConfigurado, AlmacenRespaldoError) as exc:
        print(f"[respaldo] ERROR: {exc}")
        return 1
    print(
        f"[respaldo] OK {res.clave} ({res.bytes / 1_048_576:.1f} MB); "
        f"borrados por antigüedad: {len(res.borrados)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
