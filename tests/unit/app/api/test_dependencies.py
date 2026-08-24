"""Unit test for the real get_unit_of_work wiring.

Every API integration test replaces `get_unit_of_work` via
`app.dependency_overrides` (see `tests/integration/api/conftest.py`) — on
purpose, so tests never touch `DATABASE_URL` from `.env`. That means the
real function body never runs anywhere else; this test exercises it
directly, with `database.engine.get_session_factory` monkeypatched to a
throwaway SQLite database instead of a live connection.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.models  # noqa: F401  (registers tables on Base.metadata)
from agents.ai.anthropic_provider import MODELO_POR_DEFECTO, AnthropicAIProvider
from agents.ai.openrouter_provider import OpenRouterAIProvider
from app.api.dependencies import get_ai_provider, get_unit_of_work
from core.entities.ai_configuracion import AIConfiguracion, ProveedorIA
from database.base import Base


def test_get_unit_of_work_yields_a_working_unit_of_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr("app.api.dependencies.get_session_factory", lambda: session_factory)

    generator = get_unit_of_work()
    uow = next(generator)

    assert uow.clients.get_by_id("no-existe") is None

    generator.close()


@pytest.fixture
def uow(tmp_path: Path):  # type: ignore[no-untyped-def]
    """A real `UnitOfWork` against a throwaway SQLite database."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    from database.unit_of_work import SqlAlchemyUnitOfWork

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


def test_get_ai_provider_defaults_to_anthropic_when_never_configured(uow) -> None:  # type: ignore[no-untyped-def]
    provider = get_ai_provider(uow)

    assert isinstance(provider, AnthropicAIProvider)
    assert provider._modelo == MODELO_POR_DEFECTO  # noqa: SLF001


def test_get_ai_provider_returns_openrouter_when_configured(uow) -> None:  # type: ignore[no-untyped-def]
    uow.ai_configuracion.save(
        AIConfiguracion(proveedor=ProveedorIA.OPENROUTER, modelo="deepseek/deepseek-chat")
    )
    uow.commit()

    provider = get_ai_provider(uow)

    assert isinstance(provider, OpenRouterAIProvider)
    assert provider._modelo == "deepseek/deepseek-chat"  # noqa: SLF001


def test_get_ai_provider_returns_anthropic_with_the_configured_model(uow) -> None:  # type: ignore[no-untyped-def]
    uow.ai_configuracion.save(
        AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo="claude-sonnet-5")
    )
    uow.commit()

    provider = get_ai_provider(uow)

    assert isinstance(provider, AnthropicAIProvider)
    assert provider._modelo == "claude-sonnet-5"  # noqa: SLF001
