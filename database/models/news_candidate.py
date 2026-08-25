"""ORM model for NewsCandidate.

Maps to the `news_candidates` table. Deliberately a separate class from
`core.entities.news_candidate.NewsCandidate` — see `database/models/client.py`
for why. Translation happens in
`database.repositories.news_candidate_repository`.

`hash` is `unique=True` — belt and suspenders on top of the application-level
check `core.services.radar_service.descubrir` already does
(`NewsCandidateRepository.exists(hash)` before every `save`): a unique
constraint means a race or a future caller that forgets that check still
can't create two rows for the same piece of news. `metadata_json` stores a
JSON-object string (a candidate's `metadata: dict[str, str]` can have an
arbitrary number of keys) — same convention
`PublicationRequestModel.etiquetas_editorial` already uses for
`tuple[str, ...]`: only the repository (de)serializes it, the domain entity
holds a real `dict`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class NewsCandidateModel(Base):
    """Table `news_candidates` — one row per discovered, not-yet-processed news item."""

    __tablename__ = "news_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
