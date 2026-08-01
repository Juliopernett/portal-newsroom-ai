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
from app.api.dependencies import get_unit_of_work
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
