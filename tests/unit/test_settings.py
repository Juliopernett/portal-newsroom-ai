"""Smoke tests for the configuration foundation."""

from __future__ import annotations

import pytest

from config.settings import Settings


def test_settings_has_sane_defaults(settings: Settings) -> None:
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("sqlite:///")


def test_settings_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"
