"""HTTP schemas for the "elegir de posts recientes" picker."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from core.entities.destino_publicacion import CanalPublicacion


class PostRedSocialOut(BaseModel):
    """One recent post offered by `GET /social/posts-recientes`."""

    id: str
    canal: CanalPublicacion
    permalink: str
    texto: str
    miniatura_url: str | None
    fecha_publicacion: datetime
