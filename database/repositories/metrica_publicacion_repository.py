"""SQLAlchemy adapter for `core.ports.metrica_publicacion_repository`."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.metrica_publicacion import MetricaPublicacion, MetricasPost
from database.models.metrica_publicacion import MetricaPublicacionModel


def _aware(value: datetime) -> datetime:
    """Re-attach UTC tzinfo SQLite drops on round trip (Postgres does not)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_model(m: MetricaPublicacion) -> MetricaPublicacionModel:
    return MetricaPublicacionModel(
        destino_id=m.destino_id,
        canal=m.canal.value,
        alcance=m.metricas.alcance,
        vistas=m.metricas.vistas,
        reacciones=m.metricas.reacciones,
        comentarios=m.metricas.comentarios,
        compartidos=m.metricas.compartidos,
        guardados=m.metricas.guardados,
        capturado_en=m.capturado_en,
    )


def _to_domain(model: MetricaPublicacionModel) -> MetricaPublicacion:
    return MetricaPublicacion(
        destino_id=model.destino_id,
        canal=CanalPublicacion(model.canal),
        metricas=MetricasPost(
            alcance=model.alcance,
            vistas=model.vistas,
            reacciones=model.reacciones,
            comentarios=model.comentarios,
            compartidos=model.compartidos,
            guardados=model.guardados,
        ),
        capturado_en=_aware(model.capturado_en),
    )


class SqlAlchemyMetricaPublicacionRepository:
    """`MetricaPublicacionRepository` on top of a SQLAlchemy `Session`."""

    def __init__(self, session: SqlAlchemySession) -> None:
        self._session = session

    def save(self, metrica: MetricaPublicacion) -> None:
        self._session.merge(_to_model(metrica))

    def list_by_destino_ids(self, destino_ids: Iterable[str]) -> list[MetricaPublicacion]:
        ids = list(destino_ids)
        if not ids:
            return []
        stmt = select(MetricaPublicacionModel).where(MetricaPublicacionModel.destino_id.in_(ids))
        return [_to_domain(m) for m in self._session.execute(stmt).scalars()]
