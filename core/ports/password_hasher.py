"""Port for password hashing/verification.

Deliberately not implemented in `core/` — Argon2id needs `argon2-cffi`, a
third-party cryptographic library, and `core/` never imports third-party
SDKs (same reason SQLAlchemy stays out of `core/entities/`). The concrete
adapter lives in `security/`.
"""

from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    """Contract for turning a plaintext password into a storable hash, and back."""

    def hash(self, password: str) -> str:
        """Return a salted hash of `password`, safe to store."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Return whether `password` matches `password_hash`."""
        ...
