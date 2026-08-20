"""Port for InformeLink persistence.

`get_by_token_hash` — never `get_by_token` — mirrors
`core.ports.session_repository.SessionRepository`: the raw token only ever
exists in the shared URL, in transit, and for the instant it takes to hash
it on either end.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.informe_link import InformeLink


class InformeLinkRepository(Protocol):
    """Contract for storing and retrieving `InformeLink` entities."""

    def save(self, link: InformeLink) -> None:
        """Persist `link`, creating or updating it as needed."""
        ...

    def get_by_token_hash(self, token_hash: str) -> InformeLink | None:
        """Return the `InformeLink` identified by `token_hash`, or `None`."""
        ...
