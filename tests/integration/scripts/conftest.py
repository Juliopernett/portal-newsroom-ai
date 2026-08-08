"""Shared fixtures for scripts/ integration tests — same shape as
tests/integration/persistence/conftest.py: a throwaway file-based SQLite
database, never the real one from `.env`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

import database.models  # noqa: F401  (registers tables on Base.metadata)
from database.base import Base
from database.engine import enable_sqlite_foreign_keys


@pytest.fixture
def sqlalchemy_engine(tmp_path: Path) -> Iterator[Engine]:
    """A SQLAlchemy engine bound to a fresh SQLite file, schema already created."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(sqlalchemy_engine: Engine) -> sessionmaker[Session]:
    """A session factory bound to `sqlalchemy_engine`, same config as `database.engine`."""
    return sessionmaker(bind=sqlalchemy_engine, autoflush=False, autocommit=False)
