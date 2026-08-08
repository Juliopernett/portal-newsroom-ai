"""Local-disk adapter for `core.ports.media_storage.MediaStorage`.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md, Decision
2). In production, `Settings.media_storage_dir` points at a Railway
Volume mounted to this service — chosen over an S3/R2 adapter to avoid
a new external account/credentials for this increment; the retention
policy (`core.services.media_asset_service.es_purgable`) keeps the
volume's total size bounded. Swapping to an object-storage adapter later
means a new class implementing this same `Protocol`, not a domain or API
change.
"""

from __future__ import annotations

from pathlib import Path


class MediaStorageKeyError(ValueError):
    """Raised when `key` would resolve outside the configured storage directory."""


class LocalDiskMediaStorage:
    """`MediaStorage` implemented by reading/writing files under a base directory."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # `key` is meant to be generated internally (never a raw filename
        # a user typed — see ADR-007 Decision 1), but this is enforced
        # again here as defense in depth: a `key` that resolves outside
        # `_base_dir` (e.g. via `../..`) is rejected rather than silently
        # followed.
        candidate = (self._base_dir / key).resolve()
        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise MediaStorageKeyError(f"key {key!r} resolves outside the storage directory")
        return candidate

    def guardar(self, key: str, contenido: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contenido)

    def leer(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def eliminar(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)
