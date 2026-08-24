"""Integration tests: SqlAlchemyAIConfiguracionRepository against a real SQLite schema."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from core.entities.ai_configuracion import AIConfiguracion, ProveedorIA
from database.repositories.ai_configuracion_repository import SqlAlchemyAIConfiguracionRepository


def _configuracion(**overrides: object) -> AIConfiguracion:
    defaults: dict[str, object] = {"proveedor": ProveedorIA.ANTHROPIC, "modelo": "claude-opus-5"}
    defaults.update(overrides)
    return AIConfiguracion(**defaults)


def test_get_returns_none_before_first_save(session: Session) -> None:
    repository = SqlAlchemyAIConfiguracionRepository(session)

    assert repository.get() is None


def test_save_and_get_round_trips(session: Session) -> None:
    repository = SqlAlchemyAIConfiguracionRepository(session)
    configuracion = _configuracion(proveedor=ProveedorIA.OPENROUTER, modelo="deepseek/deepseek-chat")

    repository.save(configuracion)
    session.commit()

    assert repository.get() == configuracion


def test_save_again_replaces_the_singleton_row_instead_of_creating_a_second_one(
    session: Session,
) -> None:
    repository = SqlAlchemyAIConfiguracionRepository(session)
    original = _configuracion()
    repository.save(original)
    session.commit()

    actualizada = replace(original, proveedor=ProveedorIA.OPENROUTER, modelo="deepseek/deepseek-chat")
    repository.save(actualizada)
    session.commit()

    resultado = repository.get()
    assert resultado is not None
    assert resultado.id == original.id
    assert resultado.proveedor == ProveedorIA.OPENROUTER
    assert resultado.modelo == "deepseek/deepseek-chat"
