"""Port for resolving a discovery URL to its real source.

Google News' RSS `link` field (and similar aggregator feeds) points at a
`news.google.com/...` redirect page, not the medium that actually
published the story. Implemented by adapters that follow that redirect
chain (HTTP, or later some other mechanism if Google changes how it
serves these links) to find the real article URL. Consumed by
`core.services.source_resolution_service`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SourceResolverError(RuntimeError):
    """Raised when a `SourceResolver` adapter cannot even attempt a resolution.

    Reserved for programmer errors (e.g. an empty `url`) — a network
    failure, timeout, or redirect loop is a normal, expected outcome and
    is reported via `ResolvedSource.success = False` instead of raising,
    so `core.services.source_resolution_service` never needs a
    try/except around a call to `resolve`.
    """


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    """Outcome of one `SourceResolver.resolve` call.

    Never raises for a failure a caller should expect (timeout, dead
    link, redirect loop, a site that blocks the request) — those are
    reported here as `success=False` with a human-readable `error`, same
    role `ContentSourceError`'s message plays for
    `core.services.radar_service.descubrir`.
    """

    success: bool
    resolved_url: str | None
    error: str | None = None


class SourceResolver(Protocol):
    """Contract for resolving a discovery URL to the real source's URL."""

    def resolve(self, url: str) -> ResolvedSource:
        """Attempt to resolve `url` to the page it ultimately points at.

        Must never raise for a resolution failure (see `ResolvedSource`)
        — only for a truly exceptional/programmer-error case, as
        `SourceResolverError`.
        """
        ...
