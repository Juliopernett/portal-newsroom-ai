"""Unit tests for database.engine."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from database.engine import enable_sqlite_foreign_keys, normalize_database_url


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "postgres://user:pass@host.railway.internal:5432/railway",
            "postgresql+psycopg://user:pass@host.railway.internal:5432/railway",
        ),
        (
            "postgresql://user:pass@host:5432/db",
            "postgresql://user:pass@host:5432/db",
        ),
        (
            "postgresql+psycopg://user:pass@host:5432/db",
            "postgresql+psycopg://user:pass@host:5432/db",
        ),
        ("sqlite:///database/newsroom.db", "sqlite:///database/newsroom.db"),
    ],
)
def test_normalize_database_url(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


def test_enable_sqlite_foreign_keys_is_a_noop_for_other_dialects() -> None:
    # No live connection needed: create_engine() never connects eagerly, and
    # this function only inspects engine.dialect.name.
    engine = create_engine("postgresql+psycopg://user:pass@localhost/db")

    enable_sqlite_foreign_keys(engine)  # must return quietly, not raise


def test_enable_sqlite_foreign_keys_actually_enforces_them() -> None:
    engine = create_engine("sqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)

    with engine.connect() as connection:
        pragma_value = connection.exec_driver_sql("PRAGMA foreign_keys").scalar()

    assert pragma_value == 1
