"""Domain services.

Pure business logic that does not naturally belong to a single entity. See
README.md for the full rationale and what does NOT belong here.

Re-exported below for ergonomic imports (`from core.services import
DiscoveryEngine`), same convention as `core/events/` and `core/entities/`.
"""

from __future__ import annotations

from core.services.deduplication import generate_candidate_hash
from core.services.discovery_engine import DiscoveryEngine
from core.services.pauta_service import PautaService
from core.services.publication_request_service import mark_as_published

__all__ = [
    "DiscoveryEngine",
    "PautaService",
    "generate_candidate_hash",
    "mark_as_published",
]
