"""Port for the off-site store that holds the database backups."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AlmacenRespaldoError(RuntimeError):
    """The backup store could not be reached or refused the request."""


class AlmacenRespaldos(Protocol):
    def subir(self, archivo: Path, clave: str) -> int:
        """Upload `archivo` as `clave`; return the size in bytes the store reports."""
        ...

    def listar(self, prefijo: str) -> list[str]:
        """Return every key under `prefijo`, oldest first."""
        ...

    def borrar(self, clave: str) -> None: ...
