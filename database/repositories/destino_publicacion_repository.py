"""SQLAlchemy adapter for `DestinoPublicacionRepository`.

Translates between `core.entities.destino_publicacion.DestinoPublicacion`
(domain) and `database.models.destino_publicacion.DestinoPublicacionModel`
(ORM). The domain never sees this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from database.models.destino_publicacion import DestinoPublicacionModel


def _to_model(destino: DestinoPublicacion) -> DestinoPublicacionModel:
    return DestinoPublicacionModel(
        id=destino.id,
        publication_request_id=destino.publication_request_id,
        canal=destino.canal.value,
        estado=destino.estado.value,
        wp_post_id=destino.wp_post_id,
        wp_url=destino.wp_url,
        url_publicacion=destino.url_publicacion,
        registrado_por_user_id=destino.registrado_por_user_id,
        fecha_publicacion=destino.fecha_publicacion,
        ultimo_error=destino.ultimo_error,
    )


def _to_domain(model: DestinoPublicacionModel) -> DestinoPublicacion:
    fecha_publicacion = model.fecha_publicacion
    if fecha_publicacion is not None and fecha_publicacion.tzinfo is None:
        # Same SQLite round-trip quirk handled in
        # database.repositories.publication_request_repository — see that
        # module's `_to_domain` for the full explanation.
        fecha_publicacion = fecha_publicacion.replace(tzinfo=UTC)
    return DestinoPublicacion(
        id=model.id,
        publication_request_id=model.publication_request_id,
        canal=CanalPublicacion(model.canal),
        estado=EstadoDestino(model.estado),
        wp_post_id=model.wp_post_id,
        wp_url=model.wp_url,
        url_publicacion=model.url_publicacion,
        registrado_por_user_id=model.registrado_por_user_id,
        fecha_publicacion=fecha_publicacion,
        ultimo_error=model.ultimo_error,
    )


class SqlAlchemyDestinoPublicacionRepository:
    """`DestinoPublicacionRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, destino: DestinoPublicacion) -> None:
        """Persist `destino`, creating or updating it as needed."""
        self._session.merge(_to_model(destino))

    def get_by_id(self, id: str) -> DestinoPublicacion | None:
        """Return the `DestinoPublicacion` identified by `id`, or `None`."""
        model = self._session.get(DestinoPublicacionModel, id)
        return _to_domain(model) if model is not None else None

    def list_by_publication_request_id(
        self, publication_request_id: str
    ) -> list[DestinoPublicacion]:
        """Return every destino belonging to `publication_request_id`."""
        stmt = select(DestinoPublicacionModel).where(
            DestinoPublicacionModel.publication_request_id == publication_request_id
        )
        models = self._session.execute(stmt).scalars().all()
        return [_to_domain(model) for model in models]

    def list_all(self) -> list[DestinoPublicacion]:
        """Return every destino in the system."""
        models = self._session.execute(select(DestinoPublicacionModel)).scalars().all()
        return [_to_domain(model) for model in models]
