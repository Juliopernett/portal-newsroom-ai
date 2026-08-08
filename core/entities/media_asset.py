"""Domain entity: one media attachment of a PublicationRequest.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md). Corrects
the Sprint 3A design, which described `MediaAsset` as a Value Object
(`type`, `url_or_path`, `mime_type`, `caption`) with no identity of its
own. Designing real storage and purge revealed it needs one: a purge run
must be able to delete one file's underlying storage key and DB row
individually — the same argument that already turned
`DestinoPublicacion` into a child entity in ADR-006, not a value object.

`storage_key` is an opaque key handed to `core.ports.media_storage`
implementations — the domain never builds filesystem paths itself, so a
malicious `nombre_archivo` can never influence where a file is written
(see ADR-007 Decision 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class MediaAssetType(StrEnum):
    """What kind of file a MediaAsset holds. Audio is deliberately out of scope."""

    IMAGEN = "imagen"
    VIDEO = "video"


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaAsset:
    """One file attached to a PublicationRequest.

    Has no lifecycle states of its own (unlike `DestinoPublicacion`) — it
    exists from upload until it is purged or manually deleted. See
    `core.services.media_asset_service.es_purgable` for the purge
    condition.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    publication_request_id: str
    tipo: MediaAssetType
    nombre_archivo: str
    content_type: str
    tamano_bytes: int
    storage_key: str
    fecha_subida: datetime = field(default_factory=lambda: datetime.now(UTC))
    subido_por_user_id: str | None = None

    def __post_init__(self) -> None:
        if not self.publication_request_id:
            raise ValueError("publication_request_id must not be empty")
        if not self.nombre_archivo:
            raise ValueError("nombre_archivo must not be empty")
        if not self.content_type:
            raise ValueError("content_type must not be empty")
        if not self.storage_key:
            raise ValueError("storage_key must not be empty")
        if self.tamano_bytes <= 0:
            raise ValueError("tamano_bytes must be positive")
