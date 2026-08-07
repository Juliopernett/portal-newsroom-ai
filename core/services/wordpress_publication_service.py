"""Domain service: build WordPress draft content and attach the result to
a DestinoPublicacion.

Sprint 4A, Increment 3 (see docs/adr/ADR-006-multichannel-publication.md,
Decision 4). Depends only on `core.ports.cms_publisher.CMSPublisher`
(a `Protocol`), never on `agents.wordpress.client` directly — the real
adapter is wired in `app/api/dependencies.py`, so this module stays
testable with a fake publisher, no network, per docs/PROJECT_RULES.md
rule 5.
"""

from __future__ import annotations

from dataclasses import replace

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion
from core.entities.publication_request import PublicationRequest
from core.ports.cms_publisher import CMSPublisher


def construir_contenido_wordpress(solicitud: PublicationRequest) -> dict[str, str]:
    """Return the `{title, content}` payload a CMSPublisher.create_draft needs.

    Falls back to the first 60 characters of `texto` as the title when
    `solicitud.titulo` is not set — WordPress requires a non-empty title,
    but `titulo` is optional on `PublicationRequest` (Sprint 4A, Increment 2).
    """
    return {
        "title": solicitud.titulo or solicitud.texto[:60],
        "content": solicitud.texto,
    }


def crear_borrador(
    destino: DestinoPublicacion,
    solicitud: PublicationRequest,
    cms_publisher: CMSPublisher,
) -> DestinoPublicacion:
    """Return a copy of `destino` with `wp_post_id`/`wp_url` from a new WordPress draft.

    Does not change `destino.estado` — creating a draft is not the same
    as being published (docs/PROJECT_RULES.md rule 1); `destino` stays
    `PENDIENTE`, carrying the draft's identifiers, until a human confirms
    the post actually went live (a separate step,
    `core.services.destino_publicacion_service.marcar_publicado`).

    Raises `ValueError` if `destino.canal` is not `WORDPRESS`, or if
    `destino` is already terminal (`PUBLICADO`/`CANCELADO` — no draft
    needs creating for either).
    """
    if destino.canal != CanalPublicacion.WORDPRESS:
        raise ValueError(
            f"crear_borrador only applies to canal={CanalPublicacion.WORDPRESS.value!r}, "
            f"got canal={destino.canal.value!r}"
        )
    if destino.es_terminal:
        raise ValueError(
            f"cannot create a WordPress draft for a destino already in a terminal estado "
            f"({destino.estado.value!r})"
        )
    resultado = cms_publisher.create_draft(construir_contenido_wordpress(solicitud))
    return replace(destino, wp_post_id=resultado.post_id, wp_url=resultado.url)
