"""Port for editorial team notifications.

Implemented by adapters for a specific notification channel (Telegram
today). Consumed by the future Telegram agent (`agents/telegram/`).
"""

from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    """Contract for sending a message to the editorial team."""

    def send(self, message: str) -> None:
        """Deliver `message` to the configured notification channel."""
        ...
