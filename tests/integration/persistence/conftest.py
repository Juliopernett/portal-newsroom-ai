"""Shared fixtures for persistence integration tests.

Every fixture here runs against a throwaway file-based SQLite database, not
against Railway/PostgreSQL — nothing in this environment can reach a real
Railway instance. The schema (`database/models/`) deliberately avoids any
PostgreSQL-only feature (no native `ENUM`, no JSONB, ...), so exercising
the repositories and `SqlAlchemyUnitOfWork` through the same SQLAlchemy
Core/ORM path against SQLite is a reliable proxy for how they behave
against Postgres — but it is not a substitute for running
`alembic upgrade head` against the real Railway database at least once.
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


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A single open session for tests that talk to one repository directly."""
    session = session_factory()
    yield session
    session.close()
