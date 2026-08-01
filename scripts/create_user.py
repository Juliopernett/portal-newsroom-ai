"""Create a User who can log into Portal Newsroom AI.

No invitations, no self-registration, no admin endpoint in this sprint
(see docs/adr/ADR-005-authentication.md) — this script is the only way
to provision an account. Idempotent: running it again with an email that
already exists reports that and makes no changes, rather than silently
overwriting an existing password.

Usage:
    python -m scripts.create_user --email editor@portalvallenato.com --nombre "Editor de Turno"

Prompts for the password interactively — never accepted as a CLI
argument, since shell history and process listings are not a safe place
for a plaintext password.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from core.entities.user import User
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from security.password_hasher import Argon2IdPasswordHasher
from shared.logger import get_logger

logger = get_logger(__name__)

_MIN_PASSWORD_LENGTH = 8


def create_user(*, email: str, nombre: str, password: str) -> None:
    """Persist a new `User`, unless `email` is already registered."""
    hasher = Argon2IdPasswordHasher()
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        if uow.users.get_by_email(email) is not None:
            logger.info("Ya existe un usuario con email %s — no se hicieron cambios.", email)
            return
        user = User(email=email, password_hash=hasher.hash(password), nombre=nombre)
        uow.users.save(user)
        uow.commit()
    logger.info("Usuario creado: %s (%s).", email, nombre)


def main() -> None:
    """Parse arguments, prompt for a password, and create the user."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Contraseña: ")
    if len(password) < _MIN_PASSWORD_LENGTH:
        print(
            f"La contraseña debe tener al menos {_MIN_PASSWORD_LENGTH} caracteres.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if password != getpass.getpass("Confirmar contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        raise SystemExit(1)

    create_user(email=args.email, nombre=args.nombre, password=password)


if __name__ == "__main__":
    main()
