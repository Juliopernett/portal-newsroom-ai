"""Application settings.

Every runtime setting must be declared here and sourced from environment
variables (see `.env.example`). No module outside this file should read
`os.environ` directly — this is the single source of truth for
configuration, per docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = f"sqlite:///{BASE_DIR / 'database' / 'newsroom.db'}"

    # --- WordPress (used by the future WordPress agent) ---
    wordpress_site_url: str | None = None
    wordpress_username: str | None = None
    wordpress_app_password: str | None = None

    # --- Telegram (used by the future Telegram agent) ---
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # --- AI providers (used by the future Writer / SEO / AI Orchestrator agents) ---
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # --- Paths ---
    logs_dir: Path = BASE_DIR / "logs"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of the application settings."""
    return Settings()
