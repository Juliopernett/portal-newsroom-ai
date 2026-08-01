"""Unit tests for the User entity."""

from __future__ import annotations

import pytest

from core.entities.user import User


def _build(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "editor@portalvallenato.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fake",
        "nombre": "Editor de Turno",
    }
    defaults.update(overrides)
    return User(**defaults)


def test_create_user_assigns_defaults() -> None:
    user = _build()

    assert user.id
    assert user.created_at


def test_create_user_accepts_explicit_values() -> None:
    user = _build(id="user-1")

    assert user.id == "user-1"


@pytest.mark.parametrize("email", ["", "not-an-email"])
def test_create_user_rejects_an_invalid_email(email: str) -> None:
    with pytest.raises(ValueError, match="email"):
        _build(email=email)


def test_create_user_rejects_empty_password_hash() -> None:
    with pytest.raises(ValueError, match="password_hash"):
        _build(password_hash="")


def test_create_user_rejects_empty_nombre() -> None:
    with pytest.raises(ValueError, match="nombre"):
        _build(nombre="")


def test_user_is_immutable() -> None:
    user = _build()

    with pytest.raises(AttributeError):
        user.nombre = "Otro nombre"  # type: ignore[misc]
