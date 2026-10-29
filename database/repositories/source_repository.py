"""SQLAlchemy adapter for `core.ports.source_repository.SourceRepository`.

Translates between `core.entities.source.Source` (domain) and
`database.models.source.SourceModel` (ORM). The domain never sees this module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.source import Source
from database.models.source import SourceModel


def _to_model(source: Source) -> SourceModel:
    return SourceModel(
        id=source.id,
        name=source.name,
        type=source.type,
        url=source.url,
        enabled=source.enabled,
        priority=source.priority,
        last_scan=source.last_scan,
        intervalo_minutos=source.intervalo_minutos,
        max_items=source.max_items,
        max_age_days=source.max_age_days,
        last_error=source.last_error,
        errores_consecutivos=source.errores_consecutivos,
        etag=source.etag,
        last_modified=source.last_modified,
        last_new_count=source.last_new_count,
    )


def _to_domain(model: SourceModel) -> Source:
    last_scan = model.last_scan
    if last_scan is not None and last_scan.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not).
        last_scan = last_scan.replace(tzinfo=UTC)
    return Source(
        id=model.id,
        name=model.name,
        type=model.type,
        url=model.url,
        enabled=model.enabled,
        priority=model.priority,
        last_scan=last_scan,
        intervalo_minutos=model.intervalo_minutos,
        max_items=model.max_items,
        max_age_days=model.max_age_days,
        last_error=model.last_error,
        errores_consecutivos=model.errores_consecutivos,
        etag=model.etag,
        last_modified=model.last_modified,
        last_new_count=model.last_new_count,
    )


class SqlAlchemySourceRepository:
    """`SourceRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Source) -> None:
        """Persist `entity`, creating or updating it as needed."""
        self._session.merge(_to_model(entity))

    def get_by_id(self, id: str) -> Source | None:
        """Return the `Source` identified by `id`, or `None` if not found."""
        model = self._session.get(SourceModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[Source]:
        """Return every `Source`, highest priority first, then by name."""
        stmt = select(SourceModel).order_by(SourceModel.priority.desc(), SourceModel.name)
        return [_to_domain(model) for model in self._session.execute(stmt).scalars().all()]
