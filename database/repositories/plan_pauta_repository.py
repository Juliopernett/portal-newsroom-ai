"""SQLAlchemy adapter for `PlanPautaRepository`.

Translates between `core.entities.plan_pauta.PlanPauta` (domain) and
`database.models.plan_pauta.PlanPautaModel` (ORM). The domain never sees
this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.plan_pauta import PlanPauta
from database.models.plan_pauta import PlanPautaModel


def _to_model(plan: PlanPauta) -> PlanPautaModel:
    return PlanPautaModel(
        id=plan.id,
        nombre=plan.nombre,
        cantidad_publicaciones=plan.cantidad_publicaciones,
        valor=plan.valor,
        dias_vigencia=plan.dias_vigencia,
        orden=plan.orden,
        fecha_registro=plan.fecha_registro,
    )


def _to_domain(model: PlanPautaModel) -> PlanPauta:
    fecha_registro = model.fecha_registro
    if fecha_registro.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — same fix
        # applied in database.repositories.pauta_repository.
        fecha_registro = fecha_registro.replace(tzinfo=UTC)
    return PlanPauta(
        id=model.id,
        nombre=model.nombre,
        cantidad_publicaciones=model.cantidad_publicaciones,
        valor=model.valor,
        dias_vigencia=model.dias_vigencia,
        orden=model.orden,
        fecha_registro=fecha_registro,
    )


class SqlAlchemyPlanPautaRepository:
    """`PlanPautaRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, plan: PlanPauta) -> None:
        """Persist `plan`, creating or updating it as needed."""
        self._session.merge(_to_model(plan))

    def get_by_id(self, id: str) -> PlanPauta | None:
        """Return the `PlanPauta` identified by `id`, or `None`."""
        model = self._session.get(PlanPautaModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[PlanPauta]:
        """Return every `PlanPauta`, ordered by `orden` then `nombre`."""
        models = (
            self._session.execute(
                select(PlanPautaModel).order_by(PlanPautaModel.orden, PlanPautaModel.nombre)
            )
            .scalars()
            .all()
        )
        return [_to_domain(model) for model in models]

    def delete(self, id: str) -> None:
        """Remove the `PlanPauta` row identified by `id` — a no-op if it does not exist."""
        model = self._session.get(PlanPautaModel, id)
        if model is not None:
            self._session.delete(model)
