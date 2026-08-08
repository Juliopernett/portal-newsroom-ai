"""Port for MediaAsset persistence.

`delete` exists here — unlike `DestinoPublicacionRepository`, which never
removes a row — because a `MediaAsset` really does go away: manually
(ADR-007 Decision 4, `DELETE /publication-requests/{id}/media/{media_id}`)
or via `scripts/purgar_media_expirados.py`. Same shape as
`core.ports.session_repository.SessionRepository.delete`.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.media_asset import MediaAsset


class MediaAssetRepository(Protocol):
    """Contract for storing and retrieving `MediaAsset` entities."""

    def save(self, media: MediaAsset) -> None:
        """Persist `media`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> MediaAsset | None:
        """Return the `MediaAsset` identified by `id`, or `None`."""
        ...

    def list_by_publication_request_id(self, publication_request_id: str) -> list[MediaAsset]:
        """Return every media asset attached to `publication_request_id`."""
        ...

    def list_all(self) -> list[MediaAsset]:
        """Return every media asset in the system — used by the purge script."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `MediaAsset` row identified by `id` — a no-op if it does not exist."""
        ...
