"""Domain services.

Pure business logic that does not naturally belong to a single entity. See
README.md for the full rationale and what does NOT belong here.

Re-exported below for ergonomic imports (`from core.services import
DiscoveryEngine`), same convention as `core/events/` and `core/entities/`.
"""

from __future__ import annotations

from core.services.deduplication import generate_candidate_hash
from core.services.discovery_engine import DiscoveryEngine

__all__ = [
    "DiscoveryEngine",
    "generate_candidate_hash",
]
