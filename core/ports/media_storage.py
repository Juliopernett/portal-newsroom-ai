"""Port for storing/retrieving a MediaAsset's raw file content.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md, Decision
2). Same shape as `core.ports.cms_publisher.CMSPublisher` — the domain
and the API never know *where* a file physically lives, only that it can
be saved, read back, and deleted by an opaque `key`. Not the same
concept as `core.ports.image_provider.ImageProvider` (that port is for
the still-unbuilt editorial Images agent sourcing/generating article
images — a different bounded context, per ADR-003's "organic and
commercial never converge" rule).

The chosen adapter (`agents/storage/local_disk.py`, a Railway Volume
mounted as a local directory) is deliberately not the only possible one
— swapping to an S3/R2-backed adapter later is a new implementation of
this same `Protocol`, no domain or API change.
"""

from __future__ import annotations

from typing import Protocol


class MediaStorage(Protocol):
    """Contract for saving, reading, and deleting a MediaAsset's file content."""

    def guardar(self, key: str, contenido: bytes) -> None:
        """Persist `contenido` under `key`, overwriting if `key` already exists."""
        ...

    def leer(self, key: str) -> bytes:
        """Return the bytes stored under `key`. Raises if `key` does not exist."""
        ...

    def eliminar(self, key: str) -> None:
        """Delete whatever is stored under `key`. A no-op if `key` does not exist."""
        ...
