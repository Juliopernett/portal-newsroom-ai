"""HTTP schemas for the "elegir de posts recientes" picker."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from core.entities.destino_publicacion import CanalPublicacion


class PostRedSocialOut(BaseModel):
    """One recent post offered by `GET /social/posts-recientes`.

    `coincidencia` (0.0–1.0) is only computed when the caller passed
    solicitud context (see the route's own docstring) — `None` otherwise,
    never a fabricated score. `ya_relacionada` is `True` when this post's
    `id` is already some other destino's `meta_post_id` — see
    `core.services.coincidencia_service` for the scoring rules and
    `core.entities.destino_publicacion` for why `meta_post_id` exists.
    """

    id: str
    canal: CanalPublicacion
    permalink: str
    texto: str
    miniatura_url: str | None
    fecha_publicacion: datetime
    coincidencia: float | None = None
    ya_relacionada: bool = False
