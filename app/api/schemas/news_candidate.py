"""HTTP schemas for NewsCandidate.

Only a response schema — `NewsCandidate` rows are never created via the
API (only `core.services.radar_service.descubrir`, run from
`scripts/descubrir_noticias.py`, creates them), and the three action
endpoints (`guardar`/`descartar`/`crear-noticia`) take no body — the
transition is the whole request.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.news_candidate import EstadoNewsCandidate


class NewsCandidateOut(BaseModel):
    """Response body for a `NewsCandidate`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    title: str
    url: str
    summary: str
    image_url: str | None
    published_at: datetime | None
    discovered_at: datetime
    metadata: dict[str, str]
    confidence: float
    estado: EstadoNewsCandidate
