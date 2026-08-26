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

`.../guardar`, `.../descartar`, `.../crear-noticia` each transition one
candidate's `estado` (see `core.services.news_candidate_service`) —
`crear-noticia` only marks the candidate `PROCESADO`; it does not create
an `Article` yet (Discovery 3+, see that function's own docstring).
Every route requires an authenticated session, same
`dependencies=`-at-the-router-level pattern as every other router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.news_candidate import NewsCandidateOut
from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.ports.unit_of_work import UnitOfWork
from core.services.news_candidate_service import (
    crear_noticia,
    descartar,
    guardar,
    ordenar_para_revision,
)

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
    candidate_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> NewsCandidate:
    """Mark a candidate PROCESADO — only a state transition, see `crear_noticia`'s own docstring."""
    actualizado = crear_noticia(_get_or_404(uow, candidate_id))
    uow.news_candidates.save(actualizado)
    uow.commit()
    return actualizado
