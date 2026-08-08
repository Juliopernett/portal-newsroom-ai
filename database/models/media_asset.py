"""ORM model for MediaAsset.

Maps to the `media_assets` table. Deliberately a separate class from
`core.entities.media_asset.MediaAsset` — see `database/models/client.py`
for why. Translation happens in
`database.repositories.media_asset_repository`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class MediaAssetModel(Base):
    """Table `media_assets` — one row per file attached to a solicitud."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    publication_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("publication_requests.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    fecha_subida: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    subido_por_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
