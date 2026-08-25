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

`listar_categorias`/`resolver_o_crear_etiqueta`/`subir_media` (Sprint
2026-08-21, preparación editorial con IA) round out this same class —
see `core.ports.cms_publisher.CMSPublisher`'s docstring for why these
exist on the port at all instead of being called directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from config.settings import Settings
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult, ConsultaPostCMS, EstadoPostCMS

_REQUEST_TIMEOUT_SECONDS = 30
# WordPress's own REST API cap on `per_page` — used to fetch categories in
# one page. A site with more than 100 categories would need real
# pagination, not expected for Portal Vallenato's taxonomy.
_CATEGORIAS_POR_PAGINA = 100
_CONSULTA_ERROR = ConsultaPostCMS(estado=EstadoPostCMS.ERROR, url=None, fecha_publicacion=None)


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
        api_base = f"{settings.wordpress_site_url.rstrip('/')}/wp-json/wp/v2"
        self._posts_url = f"{api_base}/posts"
        self._categories_url = f"{api_base}/categories"
        self._tags_url = f"{api_base}/tags"
        self._media_url = f"{api_base}/media"
        self._auth = (settings.wordpress_username, settings.wordpress_app_password)

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        """Create a draft post in WordPress and return its post_id and url.

        `content` must have `title` and `content` keys — see
        `core.services.wordpress_publication_service.construir_contenido_wordpress`,
        the main intended caller. `excerpt`/`slug` (strings),
        `categories`/`tags`/`featured_media` (WordPress numeric ids as
        `str`, converted to `int` on the wire here), and `meta` (a
        `dict[str, str]` — Yoast SEO's `_yoast_wpseo_title`/`_metadesc`/
        `_focuskw`, confirmed `show_in_rest: true` on this site via `wp
        eval`, 2026-08-25) are forwarded only when present, so a plain
        `{title, content}` payload behaves exactly as before this method
        grew. Raises `requests.HTTPError` on a non-2xx response (invalid
        credentials, unreachable site, ...).
        """
        payload: dict[str, Any] = {
            "title": content["title"],
            "content": content["content"],
            "status": "draft",
        }
        if "excerpt" in content:
            payload["excerpt"] = content["excerpt"]
        if "slug" in content:
            payload["slug"] = content["slug"]
        if "categories" in content:
            payload["categories"] = [int(c) for c in content["categories"]]
        if "tags" in content:
            payload["tags"] = [int(t) for t in content["tags"]]
        if "featured_media" in content:
            payload["featured_media"] = int(content["featured_media"])
        if "meta" in content:
            payload["meta"] = dict(content["meta"])
        response = requests.post(
            self._posts_url, json=payload, auth=self._auth, timeout=_REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        return CMSDraftResult(post_id=str(data["id"]), url=data["link"])

    def listar_categorias(self) -> list[CategoriaCMS]:
        """Return every category defined in WordPress (up to 100)."""
        response = requests.get(
            self._categories_url,
            params={"per_page": _CATEGORIAS_POR_PAGINA},
            auth=self._auth,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [CategoriaCMS(id=str(c["id"]), nombre=c["name"]) for c in response.json()]

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        """Return the id of the WordPress tag named `nombre`, creating it if needed.

        WordPress's own tag search (`search=`) is a best-effort text match, not a
        guaranteed lookup — confirmed live (2026-08-25) that creating a tag whose
        name/slug already exists, even when the prior search somehow missed it,
        makes WordPress reject the `POST` with `400 {"code": "term_exists",
        "data": {"term_id": ...}}` rather than silently reusing it. That id is
        exactly what this method needs, so a `term_exists` conflict is treated as
        a successful resolution instead of an error — the real failure mode this
        guards against is `preparar_y_crear_borrador` aborting an otherwise-fine
        draft over a tag WordPress already has.
        """
        busqueda = requests.get(
            self._tags_url,
            params={"search": nombre},
            auth=self._auth,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        busqueda.raise_for_status()
        coincidencia = next(
            (t for t in busqueda.json() if t["name"].lower() == nombre.lower()), None
        )
        if coincidencia is not None:
            return str(coincidencia["id"])
        creacion = requests.post(
            self._tags_url,
            json={"name": nombre},
            auth=self._auth,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if creacion.status_code == 400:
            datos_error = creacion.json()
            if datos_error.get("code") == "term_exists":
                term_id = datos_error.get("data", {}).get("term_id")
                if term_id is not None:
                    return str(term_id)
        creacion.raise_for_status()
        return str(creacion.json()["id"])

    def subir_media(self, contenido: bytes, nombre_archivo: str, content_type: str) -> str:
        """Upload a file to WordPress's media library and return its attachment id.

        Sent as the raw request body with `Content-Disposition`, WordPress's
        own documented convention for `POST /wp-json/wp/v2/media` — not a
        multipart form.
        """
        response = requests.post(
            self._media_url,
            data=contenido,
            headers={
                "Content-Disposition": f'attachment; filename="{nombre_archivo}"',
                "Content-Type": content_type,
            },
            auth=self._auth,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return str(response.json()["id"])

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        """Return the real current state of a WordPress post.

        `context=edit` is required for WordPress to return the post at all
        while it's `draft`/`trash` (the default `context=view` only
        returns `publish`ed posts) — same Application Password used
        everywhere else in this adapter already has `edit_posts`
        capability. Never raises: network errors, a 404 (post no longer
        exists), and any other non-2xx all map to `EstadoPostCMS.ERROR`.
        """
        try:
            response = requests.get(
                f"{self._posts_url}/{post_id}",
                params={"context": "edit"},
                auth=self._auth,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            return _CONSULTA_ERROR
        if not response.ok:
            return _CONSULTA_ERROR
        data = response.json()
        estado_wp = data.get("status")
        if estado_wp == "publish":
            fecha_gmt = data.get("date_gmt")
            fecha_publicacion = (
                datetime.fromisoformat(fecha_gmt).replace(tzinfo=UTC) if fecha_gmt else None
            )
            return ConsultaPostCMS(
                estado=EstadoPostCMS.PUBLICADO, url=data.get("link"), fecha_publicacion=fecha_publicacion
            )
        if estado_wp == "trash":
            return ConsultaPostCMS(estado=EstadoPostCMS.ELIMINADO, url=None, fecha_publicacion=None)
        return ConsultaPostCMS(estado=EstadoPostCMS.BORRADOR, url=None, fecha_publicacion=None)
