"""Canned `SocialMediaReader` — stands in until the real Graph API adapter exists.

Every post this returns is prefixed `[DEMO]`, deliberately: nothing here
is a real Portal Vallenato post, and an operator picking from this list
must never be able to mistake one for genuine data. Once the real adapter
(Graph API, needs a Page Access Token + Instagram Business Account ID —
see this package's `__init__.py`) replaces it in
`app.api.dependencies.get_social_media_reader`, real posts simply have no
such prefix — nothing to remember to remove here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.post_red_social import PostRedSocial

_TEXTOS_FACEBOOK = [
    "[DEMO] 🔥 Nuevo sencillo pegando fuerte en todas las plataformas — la gente no para de "
    "cantarlo.",
    "[DEMO] Anoche fue una locura en tarima, gracias por tanto cariño 🙏🎶",
    "[DEMO] ¡Ya disponible el video oficial! Corre a verlo en YouTube 🎥",
    "[DEMO] Contrataciones: @ejemplo_manager 📞 300 000 0000",
    "[DEMO] Detrás de cámaras del videoclip que se viene 👀",
]

_TEXTOS_INSTAGRAM = [
    "[DEMO] Esto apenas comienza 🚀 #Vallenato",
    "[DEMO] La tarima de anoche fue otro nivel 🔥🪗",
    "[DEMO] Nuevo lanzamiento — link en la bio 🎶",
    "[DEMO] Ensayo del jueves antes del show 🎤",
    "[DEMO] Gracias por hacer de esta noche algo inolvidable 🙌",
]


def _posts(canal: CanalPublicacion, textos: list[str], ahora: datetime) -> list[PostRedSocial]:
    dominio = "facebook" if canal is CanalPublicacion.FACEBOOK else "instagram"
    return [
        PostRedSocial(
            id=f"demo-{canal.value}-{i}",
            canal=canal,
            permalink=f"https://www.{dominio}.com/demo/{canal.value}-{i}",
            texto=texto,
            miniatura_url=None,
            fecha_publicacion=ahora - timedelta(hours=i * 5 + 1),
        )
        for i, texto in enumerate(textos)
    ]


class FakeSocialMediaReader:
    """`SocialMediaReader` backed by fixed, clearly-marked demo data."""

    def posts_recientes(self, canal: CanalPublicacion, *, limite: int = 20) -> list[PostRedSocial]:
        if canal is CanalPublicacion.FACEBOOK:
            textos = _TEXTOS_FACEBOOK
        elif canal is CanalPublicacion.INSTAGRAM:
            textos = _TEXTOS_INSTAGRAM
        else:
            raise ValueError(f"no hay posts recientes para canal={canal.value!r}")
        return _posts(canal, textos, datetime.now(UTC))[:limite]
