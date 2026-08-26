"""Domain service: editorial review transitions for a NewsCandidate.

Sprint Discovery 2 (2026-08-26) — Radar Editorial. Same discipline as
`core.services.destino_publicacion_service`: entities in `core/entities/`
are immutable (`frozen=True`), every transition here returns a new
instance via `dataclasses.replace`, never mutates the one passed in.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate


def guardar(candidato: NewsCandidate) -> NewsCandidate:
    """Return a copy of `candidato` marked GUARDADO — worth a closer look later.

    Raises `ValueError` if `candidato` is already terminal (`PROCESADO`).
    """
    if candidato.es_terminal:
        raise ValueError(
            f"cannot mark as guardado a candidato already in a terminal estado "
            f"({candidato.estado.value!r})"
        )
    return replace(candidato, estado=EstadoNewsCandidate.GUARDADO)


def descartar(candidato: NewsCandidate) -> NewsCandidate:
    """Return a copy of `candidato` marked DESCARTADO — not worth covering.

    Never deletes the row — `NewsCandidateRepository` has no delete
    method at all, by design (see docs/PROJECT_RULES.md and the sprint's
    own requirement to keep the historical record for future analytics).
    Raises `ValueError` if `candidato` is already terminal (`PROCESADO`).
    """
    if candidato.es_terminal:
        raise ValueError(
            f"cannot mark as descartado a candidato already in a terminal estado "
            f"({candidato.estado.value!r})"
        )
    return replace(candidato, estado=EstadoNewsCandidate.DESCARTADO)


def crear_noticia(candidato: NewsCandidate) -> NewsCandidate:
    """Return a copy of `candidato` marked PROCESADO — headed into the editorial flow.

    Deliberately only a state transition this sprint — it does **not**
    create an `Article` or `EditorialTask`. Neither has a repository/port
    /`UnitOfWork` entry yet, and building that persistence now would be
    exactly the "gran desarrollo" this sprint's scope explicitly excludes
    (Extractor/Writer are Discovery 3+). `PROCESADO` is the visible,
    queryable signal a future sprint's pipeline starts from. Per
    docs/PROJECT_RULES.md rule 1, nothing about this transition publishes
    or generates content — it only marks a human decision.

    Raises `ValueError` if `candidato` is already terminal (`PROCESADO`)
    — rule 11, no news item is processed twice.
    """
    if candidato.es_terminal:
        raise ValueError(
            f"cannot mark as procesado a candidato already in a terminal estado "
            f"({candidato.estado.value!r})"
        )
    return replace(candidato, estado=EstadoNewsCandidate.PROCESADO)


def ordenar_para_revision(candidatos: Sequence[NewsCandidate]) -> list[NewsCandidate]:
    """Return `candidatos` ordered nuevos-primero, luego más recientes.

    Pure, no I/O — same style as `DiscoveryEngine._order`. `NUEVO`
    candidates sort before everything else (among themselves, most
    recently discovered first); everything already reviewed follows,
    also most-recent-first.
    """
    return sorted(
        candidatos,
        key=lambda c: (c.estado != EstadoNewsCandidate.NUEVO, -c.discovered_at.timestamp()),
    )
