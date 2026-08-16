"""SQLAlchemy adapter for `OtroIngresoRepository`.

Translates between `core.entities.otro_ingreso.OtroIngreso` (domain) and
`database.models.otro_ingreso.OtroIngresoModel` (ORM). The domain never
sees this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.otro_ingreso import OtroIngreso
from database.models.otro_ingreso import OtroIngresoModel


def _to_model(ingreso: OtroIngreso) -> OtroIngresoModel:
    return OtroIngresoModel(
        id=ingreso.id,
        origen=ingreso.origen,
        monto=ingreso.monto,
        monto_usd=ingreso.monto_usd,
        fecha_cobro=ingreso.fecha_cobro,
        observaciones=ingreso.observaciones,
        fecha_registro=ingreso.fecha_registro,
    )


def _to_domain(model: OtroIngresoModel) -> OtroIngreso:
    fecha_registro = model.fecha_registro
    if fecha_registro.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — same fix
        # applied in database.repositories.gasto_repository.
        fecha_registro = fecha_registro.replace(tzinfo=UTC)
    return OtroIngreso(
        id=model.id,
        origen=model.origen,
        monto=model.monto,
        monto_usd=model.monto_usd,
        fecha_cobro=model.fecha_cobro,
        observaciones=model.observaciones,
        fecha_registro=fecha_registro,
    )


class SqlAlchemyOtroIngresoRepository:
    """`OtroIngresoRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, ingreso: OtroIngreso) -> None:
        """Persist `ingreso`, creating or updating it as needed."""
        self._session.merge(_to_model(ingreso))

    def get_by_id(self, id: str) -> OtroIngreso | None:
        """Return the `OtroIngreso` identified by `id`, or `None`."""
        model = self._session.get(OtroIngresoModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[OtroIngreso]:
        """Return every `OtroIngreso` — the registro screen and the rentabilidad report."""
        models = self._session.execute(select(OtroIngresoModel)).scalars().all()
        return [_to_domain(model) for model in models]

    def delete(self, id: str) -> None:
        """Remove the `OtroIngreso` row identified by `id` — a no-op if it does not exist."""
        model = self._session.get(OtroIngresoModel, id)
        if model is not None:
            self._session.delete(model)
