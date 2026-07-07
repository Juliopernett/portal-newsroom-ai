"""Application entrypoint.

This will grow into the composition root that wires agents into workflows
(see docs/ROADMAP.md). For now it only proves the foundation (config ->
logging) is wired correctly end to end. Run with:

    python -m app.main
"""

from __future__ import annotations

from app.bootstrap import bootstrap
from shared.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Initialize the foundation. No agents or workflows are wired up yet."""
    bootstrap()
    logger.info("Foundation initialized successfully. No agents are wired up yet.")


if __name__ == "__main__":
    main()
