"""Domain entity: a short-lived, revocable link to share a Pauta's closing
report (`informe.pdf`) outside the app — e.g. via WhatsApp — without the
recipient needing to log in.

Server-side, stored in Postgres — same discipline
`core.entities.session.Session` already uses, for the same reason: a
stolen/leaked link can't be turned back into a working one by reading the
database, and an operator can always let it expire rather than needing a
denylist. `token_hash` is never the raw token the shared URL carries — see
`core.ports.informe_link_repository.InformeLinkRepository`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class InformeLink:
    """A single share link for one Pauta's informe, valid until `expires_at`."""

    id: str = field(default_factory=lambda: str(uuid4()))
    pauta_id: str
    token_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.pauta_id:
            raise ValueError("pauta_id must not be empty")
        if not self.token_hash:
            raise ValueError("token_hash must not be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
