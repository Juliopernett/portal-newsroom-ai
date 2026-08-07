"""Domain services.

Pure business logic that does not naturally belong to a single entity. See
README.md for the full rationale and what does NOT belong here.

Re-exported below for ergonomic imports (`from core.services import
DiscoveryEngine`), same convention as `core/events/` and `core/entities/`.
"""

from __future__ import annotations

from core.services.deduplication import generate_candidate_hash
from core.services.destino_publicacion_service import (
    cancelar,
    esta_completa,
    marcar_fallido,
    marcar_publicado,
)
from core.services.discovery_engine import DiscoveryEngine
from core.services.pauta_service import PautaService
from core.services.publication_request_service import aceptar, cerrar_si_completa

__all__ = [
    "DiscoveryEngine",
    "PautaService",
    "aceptar",
    "cancelar",
    "cerrar_si_completa",
    "esta_completa",
    "generate_candidate_hash",
    "marcar_fallido",
    "marcar_publicado",
]
