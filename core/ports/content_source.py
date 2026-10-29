"""Port for content discovery sources.

Implemented by adapters that watch external sources (RSS feeds, news sites,
etc.) for new content. Consumed by
`core.services.discovery_engine.DiscoveryEngine` and, eventually, by the
Radar agent (`agents/radar/`).

Sprint 2 note: this port originally returned bare reference strings
(`list[str]`), before `core.entities.NewsCandidate` existed. Now that it
does, adapters return structured candidates directly — nothing implemented
this port yet (`agents/radar/` is still a placeholder), so this is a
straightforward refinement, not a breaking change to running code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source


@dataclass(frozen=True, slots=True)
class ResultadoFetch:
    """Outcome of a conditional fetch (Sprint Fuentes, 2026-10-29).

    `not_modified` means the source answered "nothing changed since the
    `etag`/`last_modified` I sent" — no body was downloaded and
    `candidates` is empty. `etag`/`last_modified` are the validators to
    send on the next fetch (kept as they were when `not_modified`).
    """

    candidates: list[NewsCandidate] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


class ContentSourceError(RuntimeError):
    """Raised when a `ContentSource` adapter cannot fetch or parse its source.

    Covers network failure, a non-2xx response, or a feed/page whose
    content is too broken to use — same role `AIProviderError` plays for
    `core.ports.ai_provider`: lives on the port so a caller (e.g.
    `core.services.radar_service.descubrir`) can catch one domain-level
    exception without importing whatever HTTP/parsing library the
    concrete adapter happens to use.
    """


class ContentSource(Protocol):
    """Contract for anything capable of reporting newly discovered content.

    Concrete adapters (an RSS reader, a site crawler, an API poller, a test
    fixture reader, ...) implement this protocol. `DiscoveryEngine` depends
    only on this interface, never on a specific source implementation.
    """

    @property
    def source(self) -> Source:
        """The `Source` configuration this adapter fetches on behalf of."""
        ...

    def fetch_candidates(self) -> list[NewsCandidate]:
        """Return the candidates currently available from this source.

        An adapter may also offer `fetch_condicional(etag, last_modified) ->
        ResultadoFetch`; `core.services.source_scan_service` uses it when present
        so an unchanged source costs one tiny request instead of a full download.

        Adapters are responsible for computing each candidate's `hash` (see
        `core.services.deduplication`) — deduplicating across sources is
        `DiscoveryEngine`'s job, not this port's.
        """
        ...
