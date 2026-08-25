"""Domain service: run one real discovery pass and persist what is new.

Sprint Discovery 1 (2026-08-25) — the first piece of Radar that actually
exists (see `agents/radar/README.md`). `descubrir` is the thin
orchestration `DiscoveryEngine` itself deliberately doesn't do: it calls
`DiscoveryEngine.run` (unchanged, still only aggregates/dedups-within-pass/
orders — see `core.services.discovery_engine`), then persists only the
candidates `NewsCandidateRepository` doesn't already know about (dedup
*between* passes, which `DiscoveryEngine` explicitly leaves to
`core.ports.repository.Repository`, per docs/PROJECT_RULES.md rule 11).

Depends only on ports (`ContentSource`, `NewsCandidateRepository`) — no
network, no SQLAlchemy import here, same discipline as
`core.services.wordpress_publication_service`.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.ports.content_source import ContentSource, ContentSourceError
from core.ports.news_candidate_repository import NewsCandidateRepository
from core.services.discovery_engine import DiscoveryEngine
from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoDescubrimiento:
    """What one `descubrir` call found, for a human or a future caller to read."""

    fuente: str
    consultados: int
    nuevos: int
    duplicados: int
    errores: int


def descubrir(
    source: ContentSource,
    repository: NewsCandidateRepository,
    engine: DiscoveryEngine | None = None,
) -> ResultadoDescubrimiento:
    """Run one discovery pass over `source`, persisting only new candidates.

    Never raises for a source-level failure (`ContentSourceError`) — it is
    caught, logged, and reflected as `errores=1` instead, so a future
    caller looping over several sources can keep going after one fails.
    `consultados` counts candidates after `DiscoveryEngine`'s own
    within-pass dedup by hash — a real RSS/Atom feed essentially never
    repeats an entry within one fetch, so this stays a faithful count of
    what the source actually reported without a second fetch just to
    measure the raw total.
    """
    engine = engine if engine is not None else DiscoveryEngine()
    fuente_nombre = source.source.name
    try:
        news_found = engine.run([source])
    except ContentSourceError as exc:
        logger.warning("Fuente '%s' no disponible: %s", fuente_nombre, exc)
        return ResultadoDescubrimiento(
            fuente=fuente_nombre, consultados=0, nuevos=0, duplicados=0, errores=1
        )

    nuevos = 0
    duplicados = 0
    for candidato in news_found.candidates:
        if repository.exists(candidato.hash):
            duplicados += 1
        else:
            repository.save(candidato)
            nuevos += 1

    consultados = len(news_found.candidates)
    logger.info(
        "Descubrimiento en '%s': %d consultado(s), %d nuevo(s), %d duplicado(s)",
        fuente_nombre,
        consultados,
        nuevos,
        duplicados,
    )
    return ResultadoDescubrimiento(
        fuente=fuente_nombre,
        consultados=consultados,
        nuevos=nuevos,
        duplicados=duplicados,
        errores=0,
    )
