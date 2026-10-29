"""ORM model for Source (Sprint Fuentes, 2026-10-29).

Maps to the `sources` table. Deliberately a separate class from
`core.entities.source.Source` — see `database/models/client.py` for why.
`NewsCandidateModel.source` stores this table's `id` as a plain string (no
foreign key, same convention as the rest of `database/models/`), so a
source can be disabled but its candidates' history is never orphaned.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class SourceModel(Base):
    """Table `sources` — one row per place the Radar scans."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intervalo_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_items: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    errores_consecutivos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)
    last_new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
