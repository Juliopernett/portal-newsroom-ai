"""Port for content discovery sources.

Implemented by adapters that watch external sources (RSS feeds, news sites,
etc.) for new content. Consumed by the future Radar agent
(`agents/radar/`).
"""

from __future__ import annotations

from typing import Protocol


class ContentSource(Protocol):
    """Contract for anything capable of reporting newly available content.

    Concrete adapters (an RSS reader, a site crawler, an API poller, ...)
    implement this protocol. The Radar agent will depend only on this
    interface, never on a specific source implementation.
    """

    def fetch_new_references(self) -> list[str]:
        """Return identifiers (e.g. URLs) for content available right now.

        Deduplication against previously processed content is the caller's
        responsibility (see `core.ports.repository.Repository`), not this
        port's.
        """
        ...
