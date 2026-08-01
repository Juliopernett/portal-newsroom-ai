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

from typing import Protocol

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source


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

        Adapters are responsible for computing each candidate's `hash` (see
        `core.services.deduplication`) — deduplicating across sources is
        `DiscoveryEngine`'s job, not this port's.
        """
        ...
