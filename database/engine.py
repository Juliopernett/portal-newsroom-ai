"""Database engine and session factory.

This module owns the single SQLAlchemy engine used by the application. No
other module should call `create_engine` directly — go through
`get_engine()` / `get_session_factory()` so connection settings stay
centralized. Swapping SQLite for PostgreSQL (Sprint 3C, Railway) is a
one-line change in `.env` (`DATABASE_URL`), not code — see
`docs/product/SAAS_EVOLUTION.md` and `docs/product/MVP_SCOPE.md`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings


def normalize_database_url(database_url: str) -> str:
    """Rewrite a driver-less Postgres URL to explicitly use `psycopg` (v3).

    Two distinct real-world cases, both observed from actual Railway
    `DATABASE_URL` values, not just Railway's docs:

    - `postgres://...` — the legacy scheme Railway/Heroku have historically
      handed out. SQLAlchemy 2.0 rejects it outright.
    - `postgresql://...` — Railway's *current* internal `DATABASE_URL`
      (e.g. `${{Postgres.DATABASE_URL}}`) uses this, valid but driver-less.
      SQLAlchemy 2.0 accepts it and silently defaults to `psycopg2`, which
      this project does not install (see `requirements.txt`,
      `psycopg[binary]`, the v3 driver) — this failed an actual deploy
      before this fix (`ModuleNotFoundError: No module named 'psycopg2'`).

    A URL that already names a driver (`postgresql+psycopg://`,
    `postgresql+asyncpg://`, ...) is left untouched.
    """
    scheme, separator, rest = database_url.partition("://")
    if separator and scheme in ("postgres", "postgresql"):
        return f"postgresql+psycopg://{rest}"
    return database_url


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    """Turn on SQLite foreign key enforcement — off by default, unlike PostgreSQL.

    Without this, an invalid `client_id`/`pauta_id` reference would silently
    succeed against the SQLite databases used locally and in tests, while
    correctly failing against the PostgreSQL/Railway database used in
    production — a behavior gap that would hide real bugs until deploy.
    No-op for every other dialect.
    """
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        # `Any`: the raw DBAPI connection type varies per driver and SQLAlchemy's
        # own "connect" event does not type it more precisely than this.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


@lru_cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine built from the application settings."""
    settings = get_settings()
    database_url = normalize_database_url(settings.database_url)
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args)
    enable_sqlite_foreign_keys(engine)
    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached session factory bound to the application engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
