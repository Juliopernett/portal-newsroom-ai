"""SQLAlchemy adapter for `PublicationRequestRepository`.

Translates between `core.entities.publication_request.PublicationRequest`
(domain) and `database.models.publication_request.PublicationRequestModel`
(ORM). The domain never sees this module.
"""

from __future__ import annotations

import json
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.publication_request import (
    EstadoPreparacionIA,
    PublicationRequest,
    PublicationRequestStatus,
)
from database.models.publication_request import PublicationRequestModel


def _to_model(solicitud: PublicationRequest) -> PublicationRequestModel:
    return PublicationRequestModel(
        id=solicitud.id,
        pauta_id=solicitud.pauta_id,
        client_id=solicitud.client_id,
        fecha_recepcion=solicitud.fecha_recepcion,
        titulo=solicitud.titulo,
        texto=solicitud.texto,
        estado=solicitud.estado.value,
        prioridad_manual=solicitud.prioridad_manual,
        observaciones=solicitud.observaciones,
        fecha_cierre=solicitud.fecha_cierre,
        contenido_editorial=solicitud.contenido_editorial,
        entradilla_editorial=solicitud.entradilla_editorial,
        titulo_editorial=solicitud.titulo_editorial,
        categoria_editorial=solicitud.categoria_editorial,
        etiquetas_editorial=(
            json.dumps(list(solicitud.etiquetas_editorial))
            if solicitud.etiquetas_editorial is not None
            else None
        ),
        slug_editorial=solicitud.slug_editorial,
        meta_titulo_editorial=solicitud.meta_titulo_editorial,
        meta_descripcion_editorial=solicitud.meta_descripcion_editorial,
        frase_clave_editorial=solicitud.frase_clave_editorial,
        preparacion_ia_estado=solicitud.preparacion_ia_estado.value,
        preparacion_ia_error=solicitud.preparacion_ia_error,
    )


def _to_domain(model: PublicationRequestModel) -> PublicationRequest:
    fecha_recepcion = model.fecha_recepcion
    if fecha_recepcion.tzinfo is None:
        # SQLite has no native timezone-aware timestamp type and silently
        # drops tzinfo on round trip (Postgres does not). The domain always
        # constructs `fecha_recepcion` as UTC-aware (see the entity's
        # `default_factory`), so re-attach it here rather than let a naive
        # datetime leak out of persistence on SQLite.
        fecha_recepcion = fecha_recepcion.replace(tzinfo=UTC)
    fecha_cierre = model.fecha_cierre
    if fecha_cierre is not None and fecha_cierre.tzinfo is None:
        fecha_cierre = fecha_cierre.replace(tzinfo=UTC)
    return PublicationRequest(
        id=model.id,
        pauta_id=model.pauta_id,
        client_id=model.client_id,
        fecha_recepcion=fecha_recepcion,
        titulo=model.titulo,
        texto=model.texto,
        estado=PublicationRequestStatus(model.estado),
        prioridad_manual=model.prioridad_manual,
        observaciones=model.observaciones,
        fecha_cierre=fecha_cierre,
        contenido_editorial=model.contenido_editorial,
        entradilla_editorial=model.entradilla_editorial,
        titulo_editorial=model.titulo_editorial,
        categoria_editorial=model.categoria_editorial,
        etiquetas_editorial=(
            tuple(json.loads(model.etiquetas_editorial))
            if model.etiquetas_editorial is not None
            else None
        ),
        slug_editorial=model.slug_editorial,
        meta_titulo_editorial=model.meta_titulo_editorial,
        meta_descripcion_editorial=model.meta_descripcion_editorial,
        frase_clave_editorial=model.frase_clave_editorial,
        preparacion_ia_estado=EstadoPreparacionIA(model.preparacion_ia_estado),
        preparacion_ia_error=model.preparacion_ia_error,
    )


class SqlAlchemyPublicationRequestRepository:
    """`PublicationRequestRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, solicitud: PublicationRequest) -> None:
        """Persist `solicitud`, creating or updating it as needed."""
        self._session.merge(_to_model(solicitud))

    def get_by_id(self, id: str) -> PublicationRequest | None:
        """Return the `PublicationRequest` identified by `id`, or `None`."""
        model = self._session.get(PublicationRequestModel, id)
        return _to_domain(model) if model is not None else None

    def list_by_pauta_id(self, pauta_id: str) -> list[PublicationRequest]:
        """Return every request linked to `pauta_id` — what PautaService needs."""
        stmt = select(PublicationRequestModel).where(PublicationRequestModel.pauta_id == pauta_id)
        models = self._session.execute(stmt).scalars().all()
        return [_to_domain(model) for model in models]

    def list_all(self, estado: PublicationRequestStatus | None = None) -> list[PublicationRequest]:
        """Return every request, optionally filtered to a single `estado`."""
        stmt = select(PublicationRequestModel)
        if estado is not None:
            stmt = stmt.where(PublicationRequestModel.estado == estado.value)
        models = self._session.execute(stmt).scalars().all()
        return [_to_domain(model) for model in models]
