"""Domain entity: a publication request received from a commercial Client.

What arrives over WhatsApp from a manager, artist, promoter or business
owner: text today, attachments in a later sprint (see docs/roadmap).
Deliberately scoped to commercial content only — organic content stays
entirely inside Discovery (`core.entities.news_candidate.NewsCandidate`)
and never becomes a `PublicationRequest`; the two never converge in a
shared entity, see Sprint 3B domain discovery.

A request can arrive before anyone knows which `Pauta` it belongs to:
`pauta_id` is optional while `estado` is `RECIBIDA` or `CANCELADA`, and
becomes mandatory the moment a request moves to `ACEPTADA` or `PUBLICADA`
(Sprint 3B.1 domain adjustment) — matching how triage actually happens: an
operator links a request to a `Client`'s `Pauta` before accepting it,
never before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class PublicationRequestStatus(StrEnum):
    """Lifecycle of a commercial publication request."""

    RECIBIDA = "recibida"
    ACEPTADA = "aceptada"
    PUBLICADA = "publicada"
    CANCELADA = "cancelada"


_ESTADOS_CON_PAUTA_OBLIGATORIA: frozenset[PublicationRequestStatus] = frozenset(
    {PublicationRequestStatus.ACEPTADA, PublicationRequestStatus.PUBLICADA}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationRequest:
    """A publication request, optionally tied to a Client's Pauta.

    `pauta_id` is required once `estado` is `ACEPTADA` or `PUBLICADA`, and
    optional otherwise (`RECIBIDA`, `CANCELADA`).
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    pauta_id: str | None = None
    fecha_recepcion: datetime = field(default_factory=lambda: datetime.now(UTC))
    texto: str
    estado: PublicationRequestStatus = PublicationRequestStatus.RECIBIDA
    prioridad_manual: bool = False
    observaciones: str | None = None

    def __post_init__(self) -> None:
        if self.pauta_id == "":
            raise ValueError(
                "pauta_id must not be an empty string — use None if not linked to a Pauta yet"
            )
        if not self.texto:
            raise ValueError("texto must not be empty")
        if self.estado in _ESTADOS_CON_PAUTA_OBLIGATORIA and self.pauta_id is None:
            raise ValueError(f"pauta_id is required when estado is {self.estado.value!r}")
