"""HTTP schema for MediaAsset.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md). No
`Create` schema — `POST /publication-requests/{id}/media` takes the file
itself via `multipart/form-data` (a FastAPI `UploadFile` parameter), not
a JSON body. `storage_key` is deliberately excluded from `MediaAssetOut`
— it's an internal detail of `core.ports.media_storage`, never something
a client needs or should be able to guess.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.media_asset import MediaAssetType


class MediaAssetOut(BaseModel):
    """Response body for a `MediaAsset`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    publication_request_id: str
    tipo: MediaAssetType
    nombre_archivo: str
    content_type: str
    tamano_bytes: int
    fecha_subida: datetime
    subido_por_user_id: str | None
