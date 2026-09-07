"""HTTP schemas for NewsCandidate.

Only a response schema — `NewsCandidate` rows are never created via the
API (only `core.services.radar_service.descubrir`, run from
`scripts/descubrir_noticias.py`, creates them), and the action endpoints
(`guardar`/`descartar`/`crear-noticia`/`preparar`) take no body — the
transition is the whole request.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.news_candidate import EstadoNewsCandidate, EstadoResolucionFuente


class ExtractedContentOut(BaseModel):
    """Response body for a `NewsCandidate`'s `extracted_content`, if any."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    body: str
    source_url: str
    author: str | None
    published_at: datetime | None
    site_name: str | None
    image_urls: tuple[str, ...]


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
    url_fuente_original: str | None
    estado_resolucion: EstadoResolucionFuente
    extracted_content: ExtractedContentOut | None
