"""ORM model for InformeLink.

Maps to the `informe_links` table. Deliberately a separate class from
`core.entities.informe_link.InformeLink` — see `database/models/client.py`
for why. Translation happens in `database.repositories.informe_link_repository`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class InformeLinkModel(Base):
    """Table `informe_links` — one row per share link for a Pauta's informe."""

    __tablename__ = "informe_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pauta_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pautas.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
