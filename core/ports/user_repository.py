"""Port for User persistence.

`get_by_email` exists because that is how login actually looks a user up
— there is no login flow that starts from a `User.id`.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.user import User


class UserRepository(Protocol):
    """Contract for storing and retrieving `User` entities."""

    def save(self, user: User) -> None:
        """Persist `user`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> User | None:
        """Return the `User` identified by `id`, or `None` if not found."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Return the `User` identified by `email`, or `None` if not found."""
        ...
