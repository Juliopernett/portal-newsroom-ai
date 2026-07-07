"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a Settings instance isolated from the developer's real .env."""
    return Settings(_env_file=None)
