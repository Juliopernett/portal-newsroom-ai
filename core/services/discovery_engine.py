"""Domain service: turns a set of content sources into one discovery pass.

`DiscoveryEngine` asks every enabled `ContentSource` for its candidates,
drops duplicates by content fingerprint, orders what is left, and returns
a `NewsFound` event describing the pass. It never fetches from the
network itself — that is each adapter's job — never touches persistence,
and never decides what happens next with the result; that belongs to
whatever calls it (a future `agents/radar/` + `workflows/` pipeline, see
docs/ROADMAP.md).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from core.entities.news_candidate import NewsCandidate
from core.events.news_found import NewsFound
from core.ports.content_source import ContentSource
from shared.logger import get_logger

logger = get_logger(__name__)


class DiscoveryEngine:
    """Aggregates, deduplicates and orders candidates from several sources."""

    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        """`clock` is injectable so tests can control the event's timestamp."""
        self._clock = clock

    def run(self, sources: Sequence[ContentSource]) -> NewsFound:
        """Run one discovery pass over `sources` and return a `NewsFound` event."""
        fetched = self._fetch_all(sources)
        deduplicated = self._deduplicate(fetched)
        ordered = self._order(deduplicated, sources)
        logger.info(
            "Discovery pass complete: %d fetched, %d unique candidate(s)",
            len(fetched),
            len(ordered),
        )
        return NewsFound(candidates=tuple(ordered), occurred_at=self._clock())

    def _fetch_all(self, sources: Sequence[ContentSource]) -> list[NewsCandidate]:
        candidates: list[NewsCandidate] = []
        for adapter in sources:
            if not adapter.source.enabled:
                logger.info("Skipping disabled source: %s", adapter.source.name)
                continue
            fetched = adapter.fetch_candidates()
            logger.info("Source '%s' returned %d candidate(s)", adapter.source.name, len(fetched))
            candidates.extend(fetched)
        return candidates

    @staticmethod
    def _deduplicate(candidates: list[NewsCandidate]) -> list[NewsCandidate]:
        unique_by_hash: dict[str, NewsCandidate] = {}
        for candidate in candidates:
            unique_by_hash.setdefault(candidate.hash, candidate)
        discarded = len(candidates) - len(unique_by_hash)
        if discarded:
            logger.info("Discarded %d duplicate candidate(s) by hash", discarded)
        return list(unique_by_hash.values())

    @staticmethod
    def _order(
        candidates: list[NewsCandidate], sources: Sequence[ContentSource]
    ) -> list[NewsCandidate]:
        priority_by_source = {adapter.source.id: adapter.source.priority for adapter in sources}
        return sorted(
            candidates,
            key=lambda candidate: (
                -priority_by_source.get(candidate.source, 0),
                -candidate.confidence,
                candidate.title,
            ),
        )
