"""Routes for reading back recently published social media posts.

Backs the "elegir de posts recientes" picker in `DestinosPanel` (frontend)
— see `core.ports.social_media_reader.SocialMediaReader` for why this
exists and stays strictly read-only.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_social_media_reader, get_unit_of_work
from app.api.schemas.social import PostRedSocialOut
from core.entities.destino_publicacion import CanalPublicacion
from core.ports.social_media_reader import SocialMediaReader
from core.ports.unit_of_work import UnitOfWork
from core.services.coincidencia_service import calcular_coincidencia

router = APIRouter(prefix="/social", tags=["social"], dependencies=[Depends(get_current_user)])


@router.get("/posts-recientes", response_model=list[PostRedSocialOut])
def get_posts_recientes(
    canal: CanalPublicacion,
    limite: int = 100,
    solicitud_titulo: str | None = None,
    solicitud_texto: str | None = None,
    solicitud_cliente_nombre: str | None = None,
    solicitud_fecha_recepcion: datetime | None = None,
    reader: SocialMediaReader = Depends(get_social_media_reader),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[PostRedSocialOut]:
    """Return the `limite` most recent posts for `canal` (FACEBOOK/INSTAGRAM only).

    `canal=WORDPRESS` raises `ValueError` (→ 422, the global handler) —
    there is no "recent posts" concept for a channel this app creates
    directly via `CMSPublisher`.

    Conciliación inteligente (2026-08-20): when the caller passes the
    solicitud's own `solicitud_texto`/`solicitud_fecha_recepcion` (título
    and cliente_nombre are optional extra signal), each post gets a
    `coincidencia` score via `core.services.coincidencia_service` and the
    list comes back sorted by it, most likely match first — falling back
    to plain recency when no context is given, or when scores tie (e.g.
    everything scores 0.0). Nothing here ever relates a post to a
    solicitud; that only happens via `POST .../confirmar-publicacion` or
    `PATCH .../corregir-enlace`, both requiring an explicit operator
    action. `ya_relacionada` flags a post whose id is already some other
    destino's `meta_post_id`, cross-checked against every destino in the
    system (not just this solicitud's) — so a post already claimed
    elsewhere doesn't get silently reused.
    """
    posts = reader.posts_recientes(canal, limite=limite)
    todos_los_destinos = uow.destinos_publicacion.list_all()
    ids_relacionados = {d.meta_post_id for d in todos_los_destinos if d.meta_post_id}

    resultados = [
        PostRedSocialOut(
            id=post.id,
            canal=post.canal,
            permalink=post.permalink,
            texto=post.texto,
            miniatura_url=post.miniatura_url,
            fecha_publicacion=post.fecha_publicacion,
            coincidencia=(
                calcular_coincidencia(
                    solicitud_titulo=solicitud_titulo,
                    solicitud_texto=solicitud_texto,
                    solicitud_cliente_nombre=solicitud_cliente_nombre,
                    solicitud_fecha_recepcion=solicitud_fecha_recepcion,
                    post_texto=post.texto,
                    post_fecha_publicacion=post.fecha_publicacion,
                )
                if solicitud_texto is not None and solicitud_fecha_recepcion is not None
                else None
            ),
            ya_relacionada=post.id in ids_relacionados,
        )
        for post in posts
    ]
    resultados.sort(
        key=lambda r: (
            r.coincidencia if r.coincidencia is not None else -1.0,
            r.fecha_publicacion,
        ),
        reverse=True,
    )
    return resultados
