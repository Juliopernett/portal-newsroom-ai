"""Domain entity: a post already published on Facebook/Instagram, read back
from the platform itself.

Not `core.entities.news_candidate.NewsCandidate` — that is organic content
*not yet* published, discovered from an external source for the Discovery
pillar (ADR-003: organic and commercial content never converge into one
entity). This is the opposite direction and squarely commercial: content
Portal Vallenato itself already posted, offered back as a pick so
confirming a `DestinoPublicacion`'s `url_publicacion` doesn't require
copy-pasting a link by hand (the "buscar los enlaces y pegarlos" pain the
2026-08-20 automation conversation named directly). Never persisted —
fetched live each time from `core.ports.social_media_reader.SocialMediaReader`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.entities.destino_publicacion import CanalPublicacion

_CANALES_VALIDOS = frozenset({CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM})


@dataclass(frozen=True, slots=True, kw_only=True)
class PostRedSocial:
    """One candidate post offered by the "elegir de posts recientes" picker."""

    id: str
    canal: CanalPublicacion
    permalink: str
    texto: str
    miniatura_url: str | None
    fecha_publicacion: datetime

    def __post_init__(self) -> None:
        if self.canal not in _CANALES_VALIDOS:
            canales_validos = sorted(c.value for c in _CANALES_VALIDOS)
            raise ValueError(
                f"canal must be one of {canales_validos}, got {self.canal.value!r}"
            )
        if not self.id:
            raise ValueError("id must not be empty")
        if not self.permalink:
            raise ValueError("permalink must not be empty")
