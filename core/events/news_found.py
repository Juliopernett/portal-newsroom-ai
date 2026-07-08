"""Domain event: a discovery pass finished with new, deduplicated content.

Raised by `core.services.discovery_engine.DiscoveryEngine` once it has
deduplicated and ordered the candidates gathered from a set of sources.
No event bus exists yet (see docs/ARCHITECTURE.md, section "Eventos de
dominio") — for now this is simply the return value of a discovery pass,
for whatever calls `DiscoveryEngine` to consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.entities.news_candidate import NewsCandidate


@dataclass(frozen=True, slots=True)
class NewsFound:
    """A batch of new candidates found during one Discovery Engine pass."""

    candidates: tuple[NewsCandidate, ...]
    occurred_at: datetime
