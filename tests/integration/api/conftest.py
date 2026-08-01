"""Shared fixtures for API integration tests.

Wires `app.api.main.app`'s `get_unit_of_work` dependency to a throwaway
SQLite database via `app.dependency_overrides` — FastAPI's own documented
technique for testing — so no test ever touches the real `DATABASE_URL`
from `.env`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.models  # noqa: F401  (registers tables on Base.metadata)
from app.api.dependencies import get_unit_of_work
from app.api.main import app
from database.base import Base
from database.engine import enable_sqlite_foreign_keys
from database.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient wired to a fresh SQLite database, isolated per test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _get_test_unit_of_work() -> Iterator[SqlAlchemyUnitOfWork]:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            yield uow

    app.dependency_overrides[get_unit_of_work] = _get_test_unit_of_work
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
