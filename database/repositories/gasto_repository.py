"""SQLAlchemy adapter for `GastoRepository`.

Translates between `core.entities.gasto.Gasto` (domain) and
`database.models.gasto.GastoModel` (ORM). The domain never sees this
module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.gasto import Gasto
from database.models.gasto import GastoModel


def _to_model(gasto: Gasto) -> GastoModel:
    return GastoModel(
        id=gasto.id,
        descripcion=gasto.descripcion,
        valor=gasto.valor,
        fecha=gasto.fecha,
        fecha_registro=gasto.fecha_registro,
    )


def _to_domain(model: GastoModel) -> Gasto:
    fecha_registro = model.fecha_registro
    if fecha_registro.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — same fix
        # applied in database.repositories.pauta_repository.
        fecha_registro = fecha_registro.replace(tzinfo=UTC)
    return Gasto(
        id=model.id,
        descripcion=model.descripcion,
        valor=model.valor,
        fecha=model.fecha,
        fecha_registro=fecha_registro,
    )


class SqlAlchemyGastoRepository:
    """`GastoRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, gasto: Gasto) -> None:
        """Persist `gasto`, creating or updating it as needed."""
        self._session.merge(_to_model(gasto))

    def get_by_id(self, id: str) -> Gasto | None:
        """Return the `Gasto` identified by `id`, or `None`."""
        model = self._session.get(GastoModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[Gasto]:
        """Return every `Gasto` — the registro screen and the rentabilidad report."""
        models = self._session.execute(select(GastoModel)).scalars().all()
        return [_to_domain(model) for model in models]

    def delete(self, id: str) -> None:
        """Remove the `Gasto` row identified by `id` — a no-op if it does not exist."""
        model = self._session.get(GastoModel, id)
        if model is not None:
            self._session.delete(model)
