"""Port for Session persistence.

`get_by_token_hash` — never `get_by_token` — is deliberate: the raw
session token only ever exists in the client's cookie and in memory for
the instant it takes to hash it; the stored/looked-up value is always the
hash, the same discipline `User.password_hash` already applies to
passwords, so a database leak alone can't be used to impersonate a
session.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.session import Session


class SessionRepository(Protocol):
    """Contract for storing and retrieving `Session` entities."""

    def save(self, session: Session) -> None:
        """Persist `session`, creating or updating it as needed."""
        ...

    def get_by_token_hash(self, token_hash: str) -> Session | None:
        """Return the `Session` identified by `token_hash`, or `None`."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `Session` identified by `id` — how logout works."""
        ...
