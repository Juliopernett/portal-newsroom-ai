"""Routes for reading back recently published social media posts.

Backs the "elegir de posts recientes" picker in `DestinosPanel` (frontend)
— see `core.ports.social_media_reader.SocialMediaReader` for why this
exists and stays strictly read-only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_social_media_reader
from app.api.schemas.social import PostRedSocialOut
from core.entities.destino_publicacion import CanalPublicacion
from core.entities.post_red_social import PostRedSocial
from core.ports.social_media_reader import SocialMediaReader

router = APIRouter(prefix="/social", tags=["social"], dependencies=[Depends(get_current_user)])


@router.get("/posts-recientes", response_model=list[PostRedSocialOut])
def get_posts_recientes(
    canal: CanalPublicacion,
    limite: int = 20,
    reader: SocialMediaReader = Depends(get_social_media_reader),
) -> list[PostRedSocial]:
    """Return the `limite` most recent posts for `canal` (FACEBOOK/INSTAGRAM only).

    `canal=WORDPRESS` raises `ValueError` (→ 422, the global handler) —
    there is no "recent posts" concept for a channel this app creates
    directly via `CMSPublisher`.
    """
    return reader.posts_recientes(canal, limite=limite)
