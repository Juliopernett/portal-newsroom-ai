"""Port for Client persistence.

Deliberately not built on top of `core.ports.repository.Repository` — that
generic contract (`save`/`exists`) exists for Discovery's future
deduplication needs, which `Client` does not share. `save` + `get_by_id` +
`list_all` is the entire surface the domain actually calls: `list_all`
exists because `GET /clients` (Sprint 3D, internal UI) has no other way
to show "these are your clients" — the same client-picker every other
screen (Pautas, Solicitudes) also needs.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.client import Client


class ClientRepository(Protocol):
    """Contract for storing and retrieving `Client` entities."""

    def save(self, client: Client) -> None:
        """Persist `client`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> Client | None:
        """Return the `Client` identified by `id`, or `None` if not found."""
        ...

    def list_all(self) -> list[Client]:
        """Return every `Client` — what the client picker/list needs."""
        ...
