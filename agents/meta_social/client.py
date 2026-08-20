"""Real Meta Graph API adapter for `core.ports.social_media_reader.SocialMediaReader`.

Reads back recent posts from the Facebook Page and Instagram Business
Account already connected to Portal Vallenato — never posts anything (see
`agents.wordpress.client.WordPressCMSPublisher` for the one place this
codebase creates content on an external platform, and even that only ever
creates a draft). Authenticates with a System User access token (Business
Settings → System Users → Generate token), not a personal user token —
those expire; a System User token configured without a set expiration
does not.
"""

from __future__ import annotations

from datetime import datetime

import requests

from config.settings import Settings
from core.entities.destino_publicacion import CanalPublicacion
from core.entities.post_red_social import PostRedSocial

_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
_REQUEST_TIMEOUT_SECONDS = 15
_SIN_TEXTO = "(sin texto)"


class MetaGraphConfigurationError(RuntimeError):
    """Raised when META_ACCESS_TOKEN/META_PAGE_ID/META_INSTAGRAM_BUSINESS_ACCOUNT_ID
    are not set."""


class MetaGraphSocialMediaReader:
    """`SocialMediaReader` implemented against the real Meta Graph API."""

    def __init__(self, settings: Settings) -> None:
        if not (
            settings.meta_access_token
            and settings.meta_page_id
            and settings.meta_instagram_business_account_id
        ):
            raise MetaGraphConfigurationError(
                "META_ACCESS_TOKEN, META_PAGE_ID y META_INSTAGRAM_BUSINESS_ACCOUNT_ID "
                "deben estar configurados en .env"
            )
        self._token = settings.meta_access_token
        self._page_id = settings.meta_page_id
        self._ig_id = settings.meta_instagram_business_account_id

    def posts_recientes(self, canal: CanalPublicacion, *, limite: int = 20) -> list[PostRedSocial]:
        if canal is CanalPublicacion.FACEBOOK:
            return self._posts_facebook(limite)
        if canal is CanalPublicacion.INSTAGRAM:
            return self._posts_instagram(limite)
        raise ValueError(f"no hay posts recientes para canal={canal.value!r}")

    def _get(self, path: str, *, fields: str, limite: int) -> list[dict[str, str]]:
        params: dict[str, str | int] = {
            "fields": fields,
            "limit": limite,
            "access_token": self._token,
        }
        response = requests.get(
            f"{_GRAPH_API_BASE}/{path}",
            params=params,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data: list[dict[str, str]] = response.json().get("data", [])
        return data

    def _posts_facebook(self, limite: int) -> list[PostRedSocial]:
        data = self._get(
            f"{self._page_id}/posts",
            fields="id,message,permalink_url,created_time,full_picture",
            limite=limite,
        )
        return [
            PostRedSocial(
                id=item["id"],
                canal=CanalPublicacion.FACEBOOK,
                permalink=item.get("permalink_url") or f"https://www.facebook.com/{item['id']}",
                texto=item.get("message") or _SIN_TEXTO,
                miniatura_url=item.get("full_picture"),
                fecha_publicacion=datetime.fromisoformat(item["created_time"]),
            )
            for item in data
        ]

    def _posts_instagram(self, limite: int) -> list[PostRedSocial]:
        data = self._get(
            f"{self._ig_id}/media",
            fields="id,caption,permalink,timestamp,media_url,thumbnail_url",
            limite=limite,
        )
        return [
            PostRedSocial(
                id=item["id"],
                canal=CanalPublicacion.INSTAGRAM,
                permalink=item["permalink"],
                texto=item.get("caption") or _SIN_TEXTO,
                miniatura_url=item.get("thumbnail_url") or item.get("media_url"),
                fecha_publicacion=datetime.fromisoformat(item["timestamp"]),
            )
            for item in data
        ]
