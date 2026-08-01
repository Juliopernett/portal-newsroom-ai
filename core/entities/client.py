"""Domain entity: a commercial client of Portal Vallenato.

The manager, artist, promoter or business owner who buys publication slots
(`core.entities.pauta.Pauta`) — the entity that replaces the spreadsheet
Portal Vallenato uses today to track who is who. Not the same thing as the
conceptual `MediaOutlet` from docs/product/DOMAIN_MODEL.md: `Client` is a
commercial customer *of* Portal Vallenato, not a tenant of the platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class ClientType(StrEnum):
    """What kind of commercial client this is."""

    ARTISTA = "artista"
    MANAGER = "manager"
    PROMOTOR = "promotor"
    EMPRESARIO = "empresario"


@dataclass(frozen=True, slots=True, kw_only=True)
class Client:
    """A commercial client who buys publication slots (a `Pauta`)."""

    id: str = field(default_factory=lambda: str(uuid4()))
    nombre: str
    tipo: ClientType
    telefono: str
    instagram: str | None = None
    observaciones: str | None = None

    def __post_init__(self) -> None:
        if not self.nombre:
            raise ValueError("nombre must not be empty")
        if not self.telefono:
            raise ValueError("telefono must not be empty")
