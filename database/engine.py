"""Database engine and session factory.

This module owns the single SQLAlchemy engine used by the application. No
other module should call `create_engine` directly — go through
`get_engine()` / `get_session_factory()` so connection settings stay
centralized and swapping SQLite for PostgreSQL later (docs/ROADMAP.md) is a
one-line change in `config/settings.py`.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine built from the application settings."""
    settings = get_settings()
    is_sqlite = settings.database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    return create_engine(settings.database_url, connect_args=connect_args)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached session factory bound to the application engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
