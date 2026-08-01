"""Security infrastructure (adapters).

Peer to `database/`: `database/` implements the `*_repository`/`UnitOfWork`
ports on top of SQLAlchemy; `security/` implements
`core.ports.password_hasher.PasswordHasher` on top of a cryptographic
library. Neither `core/` nor `database/` import third-party crypto —
that dependency lives only here.
"""
