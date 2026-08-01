"""Centralized logging setup.

Every module should obtain its logger via `get_logger(__name__)` rather
than configuring the `logging` module directly, so log format and
destinations stay consistent across the whole codebase (see
docs/PROJECT_RULES.md, rule 6).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import get_settings

_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=Path(settings.logs_dir) / "newsroom.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger with the project's standard configuration."""
    _configure_root_logger()
    return logging.getLogger(name)
