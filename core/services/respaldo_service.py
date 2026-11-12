"""Nightly database backup: dump, upload, check, prune.

The dump itself (`pg_dump`) is injected as a function so this logic stays
testable without a database or a network. A backup only counts when the store
reports the same number of bytes that were written — a truncated upload is an
error, never a silent success — and old backups are pruned only *after* the
new one is verified, so a failing night never costs the last good copy.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.ports.almacen_respaldos import AlmacenRespaldoError, AlmacenRespaldos

Volcado = Callable[[Path], None]


@dataclass(frozen=True, slots=True)
class ResultadoRespaldo:
    clave: str
    bytes: int
    borrados: list[str]


def clave_respaldo(prefijo: str, ahora: datetime) -> str:
    """`newsroom/2026/newsroom-2026-11-13T0300Z.dump` — sorts chronologically."""
    ahora = ahora.astimezone(UTC)
    return f"{prefijo}/{ahora:%Y}/newsroom-{ahora:%Y-%m-%dT%H%MZ}.dump"


def ejecutar_respaldo(
    volcar: Volcado,
    almacen: AlmacenRespaldos,
    *,
    prefijo: str,
    conservar: int,
    ahora: datetime | None = None,
) -> ResultadoRespaldo:
    if conservar < 1:
        raise ValueError("conservar must be at least 1")
    ahora = ahora or datetime.now(UTC)
    clave = clave_respaldo(prefijo, ahora)
    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "respaldo.dump"
        volcar(archivo)
        local = archivo.stat().st_size if archivo.exists() else 0
        if local == 0:
            raise AlmacenRespaldoError("El volcado de la base quedó vacío.")
        remoto = almacen.subir(archivo, clave)
    if remoto != local:
        raise AlmacenRespaldoError(
            f"El almacén guardó {remoto} bytes pero el volcado pesa {local}; se descarta."
        )
    existentes = sorted(almacen.listar(f"{prefijo}/"))
    sobran = [c for c in existentes if c != clave][: max(0, len(existentes) - conservar)]
    for vieja in sobran:
        almacen.borrar(vieja)
    return ResultadoRespaldo(clave=clave, bytes=local, borrados=sobran)
