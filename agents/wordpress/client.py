"""Real WordPress REST API adapter for `core.ports.cms_publisher.CMSPublisher`.

Sprint 4A, Increment 3 (see docs/adr/ADR-006-multichannel-publication.md).
Authenticates with a WordPress Application Password (WordPress core
feature since 5.6) over HTTP Basic Auth against `/wp-json/wp/v2/posts` —
no OAuth, no plugin required. Deliberately never sends `status=publish`:
every request this adapter makes creates a `draft`, per
docs/PROJECT_RULES.md rule 1 ("the system never publishes
automatically") and `CMSPublisher`'s own contract.

An Application Password is a distinct credential from the WordPress
account's login password — generated in wp-admin under the user's
profile, independently revocable. This adapter must never be configured
with a real login password.
"""

from __future__ import annotations

from typing import Any

import requests

from config.settings import Settings
from core.ports.cms_publisher import CMSDraftResult

_REQUEST_TIMEOUT_SECONDS = 30


class WordPressConfigurationError(RuntimeError):
    """Raised when WORDPRESS_SITE_URL/USERNAME/APP_PASSWORD are not set."""


class WordPressCMSPublisher:
    """`CMSPublisher` implemented against a real WordPress site's REST API."""

    def __init__(self, settings: Settings) -> None:
        if not (
            settings.wordpress_site_url
            and settings.wordpress_username
            and settings.wordpress_app_password
        ):
            raise WordPressConfigurationError(
                "WORDPRESS_SITE_URL, WORDPRESS_USERNAME y WORDPRESS_APP_PASSWORD "
                "deben estar configurados en .env"
            )
        self._posts_url = f"{settings.wordpress_site_url.rstrip('/')}/wp-json/wp/v2/posts"
        self._auth = (settings.wordpress_username, settings.wordpress_app_password)

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        """Create a draft post in WordPress and return its post_id and url.

        `content` must have `title` and `content` keys — see
        `core.services.wordpress_publication_service.construir_contenido_wordpress`,
        the only intended caller. Raises `requests.HTTPError` on a non-2xx
        response (invalid credentials, unreachable site, ...).
        """
        response = requests.post(
            self._posts_url,
            json={
                "title": content["title"],
                "content": content["content"],
                "status": "draft",
            },
            auth=self._auth,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return CMSDraftResult(post_id=str(data["id"]), url=data["link"])
