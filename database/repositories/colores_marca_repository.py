"""SQLAlchemy adapter for `ColoresMarcaRepository`."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy.orm import Session

from core.entities.colores_marca import ID_UNICO, ColoresMarca
from database.models.colores_marca import ColoresMarcaModel


class SqlAlchemyColoresMarcaRepository:
    """`ColoresMarcaRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> ColoresMarca | None:
        """Return the saved colours, or `None` if nobody changed them."""
        model = self._session.get(ColoresMarcaModel, ID_UNICO)
        if model is None:
            return None
        fecha = model.fecha_actualizacion
        return ColoresMarca(
            id=model.id,
            fondo=model.fondo,
            destacado=model.destacado,
            texto_destacado=model.texto_destacado,
            # SQLite drops tzinfo on round trip (Postgres does not).
            fecha_actualizacion=fecha if fecha.tzinfo else fecha.replace(tzinfo=UTC),
        )

    def save(self, colores: ColoresMarca) -> None:
        """Persist `colores`, creating or replacing the singleton row."""
        self._session.merge(
            ColoresMarcaModel(
                id=colores.id,
                fondo=colores.fondo,
                destacado=colores.destacado,
                texto_destacado=colores.texto_destacado,
                fecha_actualizacion=colores.fecha_actualizacion,
            )
        )
