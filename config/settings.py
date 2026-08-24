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

    # --- Auth (login MVP — see docs/adr/ADR-005-authentication.md) ---
    session_ttl_hours: int = 24 * 7

    # --- Informe compartido (enlace de WhatsApp — ver core.entities.informe_link) ---
    informe_link_ttl_dias: int = 15

    # --- WordPress (used by the future WordPress agent) ---
    wordpress_site_url: str | None = None
    wordpress_username: str | None = None
    wordpress_app_password: str | None = None

    # --- Meta Graph API (Facebook Page + Instagram Business Account —
    # "elegir de posts recientes", 2026-08-20 automation conversation).
    # A System User access token, not a personal user token — see
    # agents/meta_social/__init__.py for the permissions it needs
    # (pages_read_engagement, pages_show_list, instagram_basic). ---
    meta_access_token: str | None = None
    meta_page_id: str | None = None
    meta_instagram_business_account_id: str | None = None

    # --- Media storage (MediaAsset — see docs/adr/ADR-007-media-assets.md) ---
    # `media_storage_dir` points at a Railway Volume in production; a
    # plain local directory otherwise (see `agents/storage/local_disk.py`).
    media_storage_dir: Path = BASE_DIR / "database" / "media"
    media_max_bytes_imagen: int = 10 * 1024 * 1024  # 10 MB
    media_max_bytes_video: int = 200 * 1024 * 1024  # 200 MB
    media_retention_dias: int = 7

    # --- Telegram (used by the future Telegram agent) ---
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # --- AI providers (used by the future Writer / SEO / AI Orchestrator agents) ---
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    # OpenRouter (openrouter.ai) — aggregator exposing many providers/models
    # behind one OpenAI-compatible endpoint; selectable as an alternative to
    # Anthropic direct via Configuración → IA (see core.entities.ai_configuracion).
    openrouter_api_key: str | None = None

    # --- Paths ---
    logs_dir: Path = BASE_DIR / "logs"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of the application settings."""
    return Settings()
