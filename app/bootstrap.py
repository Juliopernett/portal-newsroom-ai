"""Application bootstrap.

Wires together the cross-cutting concerns (configuration, logging) that
every entrypoint needs before doing anything else. Agent- and
workflow-specific dependency wiring will be added here as they are
implemented (see docs/ROADMAP.md).
"""

from __future__ import annotations

from config.settings import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)


def bootstrap() -> None:
    """Initialize configuration and logging for the application."""
    settings = get_settings()
    logger.info("Portal Newsroom AI starting up (environment=%s)", settings.environment)
