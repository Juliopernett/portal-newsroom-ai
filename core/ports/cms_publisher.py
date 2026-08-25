"""Port for publishing content to a CMS.

Implemented by adapters for a specific CMS (WordPress today, potentially
another one later). Consumed by the future WordPress agent
(`agents/wordpress/`).

Per docs/PROJECT_RULES.md, this contract only exposes draft creation —
there is intentionally no `publish()` method. The system never publishes
automatically.

`create_draft` returns `CMSDraftResult` (post_id + url), not a bare
`str` — a Sprint 4A, Increment 3 change (see
docs/adr/ADR-006-multichannel-publication.md) from the original design,
which said this port would not need modifying. Building the real
WordPress adapter revealed `DestinoPublicacion` needs both `wp_post_id`
(for later status checks against the CMS) and `wp_url` (for reports and
links shared with clients) — a single opaque string could not carry
both. Zero adapters existed yet when this changed, so the change carries
no migration risk.

`listar_categorias`/`resolver_o_crear_etiqueta`/`subir_media` (Sprint
2026-08-21, preparación editorial con IA) exist so
`core.services.wordpress_publication_service.preparar_y_crear_borrador`
can build a taxonomy-aware, illustrated draft without ever importing
`agents.wordpress.client` directly — the orchestration stays testable
with a fake, per docs/PROJECT_RULES.md rule 5.

`consultar_estado_post` (Sprint 2026-08-24, sincronización de estado)
lets `core.services.destino_publicacion_service.sincronizar_estado_wordpress`
detect that an operator published a draft directly in the CMS, without
this system ever issuing a publish command itself — still a pure read,
same "never publish automatically" rule `create_draft` already follows.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, NamedTuple, Protocol


class CMSDraftResult(NamedTuple):
    """The identifier and URL of a draft just created in a CMS."""

    post_id: str
    url: str


class CategoriaCMS(NamedTuple):
    """One category already defined in the CMS — id + display name."""

    id: str
    nombre: str


class EstadoPostCMS(StrEnum):
    """The real, current state of a post in the CMS, as read back from it."""

    BORRADOR = "borrador"
    PUBLICADO = "publicado"
    ELIMINADO = "eliminado"
    ERROR = "error"


class ConsultaPostCMS(NamedTuple):
    """Result of asking the CMS for a post's real state.

    `url`/`fecha_publicacion` are only ever populated when `estado` is
    `PUBLICADO` — a draft, a trashed post, or an error carry neither.
    """

    estado: EstadoPostCMS
    url: str | None
    fecha_publicacion: datetime | None


class CMSPublisher(Protocol):
    """Contract for creating editorial drafts in a CMS.

    Implementations must never publish content directly; they only create
    drafts awaiting human review.
    """

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        """Create a draft in the CMS and return its post_id and url.

        `content` may include, besides the always-required `title`/
        `content`: `excerpt`, `slug`, `categories` (a list of
        `CategoriaCMS.id`), `tags` (a list of ids from
        `resolver_o_crear_etiqueta`), `featured_media` (an id from
        `subir_media`), and `meta` (a `dict[str, str]` of CMS-specific
        meta keys — e.g. Yoast SEO's `_yoast_wpseo_title`/`_metadesc`/
        `_focuskw` on the WordPress adapter) — every one of these is
        optional, so a caller that only has raw text still gets a plain
        draft exactly as before this contract grew.
        """
        ...

    def listar_categorias(self) -> list[CategoriaCMS]:
        """Return every category already defined in the CMS.

        Never creates a category — `core.services.editorial_ai_service`
        constrains the AI to pick only from this list (or propose none)
        so an article can never be filed under an invented taxonomy.
        """
        ...

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        """Return the id of the tag named `nombre`, creating it if needed.

        Unlike categories, tags are low-stakes and expected to grow
        organically — the CMS itself de-duplicates by slug, so calling
        this repeatedly with the same `nombre` is safe.
        """
        ...

    def subir_media(self, contenido: bytes, nombre_archivo: str, content_type: str) -> str:
        """Upload a file to the CMS's media library and return its id.

        The returned id is what `create_draft` expects as
        `featured_media`.
        """
        ...

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        """Return the real current state of a post already created via create_draft.

        Total — never raises. Any failure (network, credentials, the post
        no longer existing, an unexpected response shape) is translated to
        `EstadoPostCMS.ERROR` instead of propagating an exception, so a
        caller never has to wrap this in try/except: an ERROR is itself
        state information ("could not verify right now"), not a system
        failure.
        """
        ...
