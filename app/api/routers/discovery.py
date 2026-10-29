"""Routes for the Discovery pillar — Radar Editorial (Sprint Discovery 2).

`GET /discovery` lists `NewsCandidate`s persisted by
`core.services.radar_service.descubrir` (run via
`scripts/descubrir_noticias.py` — this API never fetches a source
itself), with optional `estado`/`q` filters, ordered nuevos-primero/
luego-más-recientes (`core.services.news_candidate_service
.ordenar_para_revision`). Filtering happens in Python after
`uow.news_candidates.list_all()`, same convention `completa` already
uses in `app.api.routers.publication_requests` — no filter is pushed
into SQL.

`.../guardar`, `.../descartar` each transition one candidate's `estado`
(see `core.services.news_candidate_service`). `.../crear-noticia`
(Sprint Discovery 5) rewrites the prepared candidate with the editorial AI
and creates a WordPress *draft* (`core.services.candidate_draft_service`),
marking it `PROCESADO`.

`.../preparar` (Sprint Discovery 3, 2026-08-29) is a separate, repeatable
technical action — `core.services.source_resolution_service
.preparar_noticia` resolves the candidate's Google News URL to its real
source and extracts that page's content. Independent of `estado`: a
candidate can be prepared before or after being guardado, and preparing
never marks it `PROCESADO` — that is still only `crear-noticia`'s job, a
deliberate separation between "get the raw material ready" (technical,
repeatable) and "send to the editorial flow" (a human's terminal
decision, see docs/PROJECT_RULES.md rule 11).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import (
    get_ai_provider,
    get_cms_publisher,
    get_content_extractor,
    get_current_user,
    get_portada_renderer,
    get_source_resolver,
    get_unit_of_work,
)
from app.api.routers.portadas import leer_imagen_subida
from app.api.schemas.news_candidate import NewsCandidateOut
from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.ports.ai_provider import AIProvider
from core.ports.cms_publisher import CMSPublisher
from core.ports.content_extractor import ContentExtractor
from core.ports.portada_renderer import PortadaRenderer, VariantePortada
from core.ports.source_resolver import SourceResolver
from core.ports.unit_of_work import UnitOfWork
from core.services.candidate_draft_service import (
    BorradorDesdeCandidatoError,
    PortadaParaBorrador,
    crear_borrador_desde_candidato,
)
from core.services.news_candidate_service import (
    descartar,
    guardar,
    ordenar_para_revision,
)
from core.services.source_resolution_service import preparar_noticia

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[NewsCandidateOut])
def list_candidatos(
    estado: EstadoNewsCandidate | None = None,
    q: str | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[NewsCandidate]:
    """Return every discovered candidate, optionally filtered by `estado` and/or `q`.

    `q` matches (case-insensitive) against `title` or `summary`.
    """
    candidatos = uow.news_candidates.list_all()
    if estado is not None:
        candidatos = [c for c in candidatos if c.estado == estado]
    if q:
        q_lower = q.lower()
        candidatos = [
            c for c in candidatos if q_lower in c.title.lower() or q_lower in c.summary.lower()
        ]
    return ordenar_para_revision(candidatos)


def _get_or_404(uow: UnitOfWork, candidate_id: str) -> NewsCandidate:
    candidato = uow.news_candidates.get_by_id(candidate_id)
    if candidato is None:
        raise HTTPException(status_code=404, detail="NewsCandidate not found")
    return candidato


@router.post("/{candidate_id}/guardar", response_model=NewsCandidateOut)
def guardar_candidato(
    candidate_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> NewsCandidate:
    """Mark a candidate GUARDADO — worth a closer look later.

    Raises 422 (via `core.services.news_candidate_service.guardar`) if
    the candidate is already `PROCESADO`.
    """
    actualizado = guardar(_get_or_404(uow, candidate_id))
    uow.news_candidates.save(actualizado)
    uow.commit()
    return actualizado


@router.post("/{candidate_id}/descartar", response_model=NewsCandidateOut)
def descartar_candidato(
    candidate_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> NewsCandidate:
    """Mark a candidate DESCARTADO — never deletes the row, keeps the history."""
    actualizado = descartar(_get_or_404(uow, candidate_id))
    uow.news_candidates.save(actualizado)
    uow.commit()
    return actualizado


@router.post("/{candidate_id}/crear-noticia", response_model=NewsCandidateOut)
def crear_noticia_desde_candidato(
    candidate_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    ai_provider: AIProvider = Depends(get_ai_provider),
    cms_publisher: CMSPublisher = Depends(get_cms_publisher),
    portada_renderer: PortadaRenderer = Depends(get_portada_renderer),
    imagen_base: UploadFile | None = File(None),
    imagen_circulo: UploadFile | None = File(None),
    variante: VariantePortada = Form(VariantePortada.NOTICIAS),
    titular_portada: str | None = Form(None, max_length=200),
    antetitulo: str | None = Form(None, max_length=60),
    enfoque_x: float = Form(0.5, ge=0, le=1),
    enfoque_y: float = Form(0.3, ge=0, le=1),
) -> NewsCandidate:
    """Rewrite the candidate with the editorial AI and create a WordPress draft.

    Optional multipart fields (Sprint Portadas): `imagen_base` (the operator's
    own photo) turns on the branded cover as the draft's featured image;
    `imagen_circulo` selects the two-photo template, `titular_portada` empty
    means "use the AI's headline". Without `imagen_base`, no image is attached.

    Sprint Discovery 5. Needs the candidate prepared first (422 otherwise).
    Never publishes — only a draft (docs/PROJECT_RULES.md rule 1); marks the
    candidate PROCESADO and stores the draft's `wp_post_id`/`wp_url`. If the
    AI fails, 502 and nothing is created; if WordPress fails, nothing is
    saved — both safely retriable.
    """
    portada = None
    if imagen_base is not None and imagen_base.filename:
        portada = PortadaParaBorrador(
            imagen_base=leer_imagen_subida(imagen_base, "imagen base"),
            variante=variante,
            titular=(titular_portada or "").strip() or None,
            antetitulo=(antetitulo or "").strip() or None,
            imagen_circulo=(
                leer_imagen_subida(imagen_circulo, "imagen del círculo")
                if imagen_circulo is not None and imagen_circulo.filename
                else None
            ),
            enfoque_x=enfoque_x,
            enfoque_y=enfoque_y,
        )
    try:
        actualizado = crear_borrador_desde_candidato(
            _get_or_404(uow, candidate_id),
            ai_provider,
            cms_publisher,
            portada=portada,
            portada_renderer=portada_renderer,
        )
    except BorradorDesdeCandidatoError as exc:
        raise HTTPException(
            status_code=502, detail=f"No se pudo redactar la noticia con IA: {exc}"
        ) from exc
    uow.news_candidates.save(actualizado)
    uow.commit()
    return actualizado


@router.post("/{candidate_id}/preparar", response_model=NewsCandidateOut)
def preparar_candidato(
    candidate_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    resolver: SourceResolver = Depends(get_source_resolver),
    extractor: ContentExtractor = Depends(get_content_extractor),
) -> NewsCandidate:
    """Resolve a candidate's real source and extract its content.

    Sprint Discovery 3. Never fails the request — a resolution or
    extraction failure is reflected in the returned candidate's
    `estado_resolucion`/`extracted_content`, never a 4xx/5xx (see
    `core.services.source_resolution_service.preparar_noticia`'s own
    docstring). Repeatable: calling this again on an already-resolved
    candidate re-resolves and re-extracts, useful if the source was
    unreachable the first time.
    """
    actualizado = preparar_noticia(_get_or_404(uow, candidate_id), resolver, extractor)
    uow.news_candidates.save(actualizado)
    uow.commit()
    return actualizado
