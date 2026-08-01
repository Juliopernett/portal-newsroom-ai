"""Argon2id adapter for `core.ports.password_hasher.PasswordHasher`.

`argon2-cffi` defaults to Argon2id (the OWASP-recommended variant) with
sane work-factor parameters — no tuning here, no reason to second-guess
the library's defaults for this team's scale.
"""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2IdPasswordHasher:
    """`PasswordHasher` implemented with Argon2id."""

    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher()

    def hash(self, password: str) -> str:
        """Return a salted Argon2id hash of `password`."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Return whether `password` matches `password_hash`.

        `InvalidHashError` (not a `VerificationError` subclass, despite the
        name — it inherits from `ValueError`) is caught alongside it: a
        malformed `password_hash` should read as "verification failed",
        never as an uncaught exception on a security-critical path.
        """
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
