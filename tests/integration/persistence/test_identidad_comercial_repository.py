"""Integration tests: SqlAlchemyIdentidadComercialRepository against a real SQLite schema."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from core.entities.identidad_comercial import IdentidadComercial
from database.repositories.identidad_comercial_repository import (
    SqlAlchemyIdentidadComercialRepository,
)


def _identidad(**overrides: object) -> IdentidadComercial:
    defaults: dict[str, object] = {
        "nombre_comercial": "Portal Vallenato",
        "razon_social": "Portal Vallenato SAS",
        "nit": "900.123.456-7",
    }
    defaults.update(overrides)
    return IdentidadComercial(**defaults)


def test_get_returns_none_before_first_save(session: Session) -> None:
    repository = SqlAlchemyIdentidadComercialRepository(session)

    assert repository.get() is None


def test_save_and_get_round_trips(session: Session) -> None:
    repository = SqlAlchemyIdentidadComercialRepository(session)
    identidad = _identidad()

    repository.save(identidad)
    session.commit()

    assert repository.get() == identidad


def test_save_again_replaces_the_singleton_row_instead_of_creating_a_second_one(
    session: Session,
) -> None:
    repository = SqlAlchemyIdentidadComercialRepository(session)
    original = _identidad()
    repository.save(original)
    session.commit()

    actualizada = replace(original, nombre_comercial="Portal Vallenato Radio")
    repository.save(actualizada)
    session.commit()

    resultado = repository.get()
    assert resultado is not None
    assert resultado.id == original.id
    assert resultado.nombre_comercial == "Portal Vallenato Radio"
