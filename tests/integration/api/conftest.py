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
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

import database.models  # noqa: F401  (registers tables on Base.metadata)
from app.api.dependencies import get_unit_of_work
from app.api.main import app
from core.entities.user import User
from database.base import Base
from database.engine import enable_sqlite_foreign_keys
from database.repositories.user_repository import SqlAlchemyUserRepository
from database.unit_of_work import SqlAlchemyUnitOfWork
from security.password_hasher import Argon2IdPasswordHasher

TEST_USER_EMAIL = "test@portalvallenato.com"
TEST_USER_PASSWORD = "a-strong-enough-test-password"


@pytest.fixture
def _test_engine(tmp_path: Path) -> Iterator[Engine]:
    """A throwaway SQLite engine, schema already created, isolated per test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def unauthenticated_client(_test_engine: Engine) -> Iterator[TestClient]:
    """A TestClient wired to a fresh SQLite database, isolated per test — no session.

    Use directly only for tests that specifically exercise the
    unauthenticated path (e.g. confirming a protected route rejects with
    401). Everything else should use `client`, which is this same fixture
    already logged in.
    """
    session_factory = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)

    def _get_test_unit_of_work() -> Iterator[SqlAlchemyUnitOfWork]:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            yield uow

    app.dependency_overrides[get_unit_of_work] = _get_test_unit_of_work
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_user(_test_engine: Engine) -> User:
    """Persist `TEST_USER_EMAIL`/`TEST_USER_PASSWORD` directly through a `Session`.

    Not via an HTTP endpoint — creating users isn't part of this sprint's
    API surface, see docs/adr/ADR-005-authentication.md. Separate from
    `client` so a test can seed the user and then drive `POST /auth/login`
    itself, instead of only ever getting an already-logged-in client.
    """
    session_factory = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)
    session: Session = session_factory()
    user = User(
        email=TEST_USER_EMAIL,
        password_hash=Argon2IdPasswordHasher().hash(TEST_USER_PASSWORD),
        nombre="Usuario de Prueba",
    )
    SqlAlchemyUserRepository(session).save(user)
    session.commit()
    session.close()
    return user


@pytest.fixture
def client(seeded_user: User, unauthenticated_client: TestClient) -> TestClient:
    """`unauthenticated_client`, already logged in as `seeded_user`.

    Logs in through the real `POST /auth/login` so every other test
    exercises the actual auth flow, not a bypass of it.
    """
    login_response = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    assert login_response.status_code == 200, login_response.text
    return unauthenticated_client
