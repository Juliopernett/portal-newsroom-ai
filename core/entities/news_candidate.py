"""Domain entity: a piece of content spotted by a source, not yet extracted.

A `NewsCandidate` is what a `core.ports.content_source.ContentSource`
reports before anyone has fetched its full body — enough to deduplicate,
rank and decide whether it is worth extracting (see
`core.services.discovery_engine.DiscoveryEngine`). The full article body
belongs to `Article`, produced later once a `ContentExtractor` and a
Writer agent have processed a candidate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class EstadoNewsCandidate(StrEnum):
    """Editorial review state of a `NewsCandidate` (Sprint Discovery 2).

    `PROCESADO` is the only terminal state — a candidate sent toward the
    editorial flow (`core.services.news_candidate_service.crear_noticia`)
    is never re-guardado/descartado/crear-noticia'd again (see
    docs/PROJECT_RULES.md, rule 11: no news item is processed twice).
    `GUARDADO`/`DESCARTADO` are not terminal relative to each other — an
    operator can change their mind either way.
    """

    NUEVO = "nuevo"
    GUARDADO = "guardado"
    DESCARTADO = "descartado"
    PROCESADO = "procesado"


_ESTADOS_TERMINALES: frozenset[EstadoNewsCandidate] = frozenset({EstadoNewsCandidate.PROCESADO})


@dataclass(frozen=True, slots=True, kw_only=True)
class NewsCandidate:
    """A candidate piece of news discovered from a single source."""

    id: str = field(default_factory=lambda: str(uuid4()))
    source: str
    title: str
    url: str
    summary: str
    image_url: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    hash: str
    metadata: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    estado: EstadoNewsCandidate = EstadoNewsCandidate.NUEVO

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence!r}")
        for required in ("id", "source", "title", "url", "hash"):
            if not getattr(self, required):
                raise ValueError(f"{required} must not be empty")

    @property
    def es_terminal(self) -> bool:
        """Return whether this candidate is done — no further review transition expected."""
        return self.estado in _ESTADOS_TERMINALES
