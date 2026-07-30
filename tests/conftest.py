"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    """Return a Settings instance isolated from the developer's real .env."""
    return Settings(_env_file=None)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the directory containing tests/fixtures/*.json sample data."""
    return FIXTURES_DIR
