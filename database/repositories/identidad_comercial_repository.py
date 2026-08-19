"""SQLAlchemy adapter for `IdentidadComercialRepository`.

Translates between `core.entities.identidad_comercial.IdentidadComercial`
(domain) and `database.models.identidad_comercial.IdentidadComercialModel`
(ORM). The domain never sees this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy.orm import Session

from core.entities.identidad_comercial import ID_UNICO, IdentidadComercial
from database.models.identidad_comercial import IdentidadComercialModel


def _to_model(identidad: IdentidadComercial) -> IdentidadComercialModel:
    return IdentidadComercialModel(
        id=identidad.id,
        nombre_comercial=identidad.nombre_comercial,
        razon_social=identidad.razon_social,
        nit=identidad.nit,
        telefono=identidad.telefono,
        email=identidad.email,
        sitio_web=identidad.sitio_web,
        instagram=identidad.instagram,
        facebook=identidad.facebook,
        otras_redes=identidad.otras_redes,
        logo_storage_key=identidad.logo_storage_key,
        logo_content_type=identidad.logo_content_type,
        fecha_actualizacion=identidad.fecha_actualizacion,
    )


def _to_domain(model: IdentidadComercialModel) -> IdentidadComercial:
    fecha_actualizacion = model.fecha_actualizacion
    if fecha_actualizacion.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — same fix
        # applied in database.repositories.pauta_repository.
        fecha_actualizacion = fecha_actualizacion.replace(tzinfo=UTC)
    return IdentidadComercial(
        id=model.id,
        nombre_comercial=model.nombre_comercial,
        razon_social=model.razon_social,
        nit=model.nit,
        telefono=model.telefono,
        email=model.email,
        sitio_web=model.sitio_web,
        instagram=model.instagram,
        facebook=model.facebook,
        otras_redes=model.otras_redes,
        logo_storage_key=model.logo_storage_key,
        logo_content_type=model.logo_content_type,
        fecha_actualizacion=fecha_actualizacion,
    )


class SqlAlchemyIdentidadComercialRepository:
    """`IdentidadComercialRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> IdentidadComercial | None:
        """Return the configured `IdentidadComercial`, or `None` if never set."""
        model = self._session.get(IdentidadComercialModel, ID_UNICO)
        return _to_domain(model) if model is not None else None

    def save(self, identidad: IdentidadComercial) -> None:
        """Persist `identidad`, creating or replacing the singleton row."""
        self._session.merge(_to_model(identidad))
