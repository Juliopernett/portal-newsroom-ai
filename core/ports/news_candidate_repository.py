"""Port for NewsCandidate persistence.

Sprint Discovery 1 (2026-08-25) — the first real use of
`core.ports.repository.Repository`, the generic contract that has existed
since Sprint 2 specifically for this: `save`/`exists` is exactly what
`core.services.radar_service.descubrir` needs to avoid persisting the same
piece of news twice across separate discovery passes (see
docs/PROJECT_RULES.md, rule 11). `list_all` is the one addition beyond the
generic contract — what a future Radar/admin view needs to see what
Discovery has found so far.

`get_by_id` (Sprint Discovery 2, 2026-08-26) — needed once Radar
Editorial's action endpoints (`guardar`/`descartar`/`crear-noticia`) had
to fetch one specific candidate to transition, same shape as
`core.ports.client_repository.ClientRepository.get_by_id`.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.news_candidate import NewsCandidate
from core.ports.repository import Repository


class NewsCandidateRepository(Repository[NewsCandidate], Protocol):
    """Contract for storing and retrieving `NewsCandidate` entities."""

    def get_by_id(self, id: str) -> NewsCandidate | None:
        """Return the `NewsCandidate` identified by `id`, or `None` if not found."""
        ...

    def list_all(self) -> list[NewsCandidate]:
        """Return every persisted `NewsCandidate`."""
        ...
