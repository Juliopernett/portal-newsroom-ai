"""Port for reading back recently published social media posts.

Backs the "elegir de posts recientes" picker (2026-08-20 automation
conversation): after publishing on Facebook/Instagram natively, an
operator confirming a `DestinoPublicacion` picks the right post from a
short recent list instead of leaving the app to find and copy its link.
Read-only, deliberately — this port never posts anything (see
`core.ports.cms_publisher.CMSPublisher` for the one place this codebase
*does* create content on an external platform, and even that only ever
creates a draft, never publishes automatically).
"""

from __future__ import annotations

from typing import Protocol

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.metrica_publicacion import MetricasPost
from core.entities.post_red_social import PostRedSocial


class SocialMediaReader(Protocol):
    """Contract for reading recent posts from a Facebook Page / Instagram
    Business account already connected to Portal Vallenato."""

    def posts_recientes(self, canal: CanalPublicacion, *, limite: int = 20) -> list[PostRedSocial]:
        """Return up to `limite` posts for `canal`, most recent first.

        `canal` must be `FACEBOOK` or `INSTAGRAM` — there is no "recent
        posts" concept for `WORDPRESS` (that channel is created directly
        by this app via `CMSPublisher`, never read back).
        """
        ...

    def metricas_post(self, canal: CanalPublicacion, post_id: str) -> MetricasPost:
        """Return what the platform reports for one already-published post.

        Any number the platform does not provide (missing permission, metric
        retired, post too old) comes back as `None`, never as zero. Raises
        `requests.RequestException` when the platform itself is unreachable.
        """
        ...
