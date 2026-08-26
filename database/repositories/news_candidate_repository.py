"""SQLAlchemy adapter for `core.ports.news_candidate_repository.NewsCandidateRepository`.

Translates between `core.entities.news_candidate.NewsCandidate` (domain)
and `database.models.news_candidate.NewsCandidateModel` (ORM). The domain
never sees this module.
"""

from __future__ import annotations

import json
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from database.models.news_candidate import NewsCandidateModel


def _to_model(candidate: NewsCandidate) -> NewsCandidateModel:
    return NewsCandidateModel(
        id=candidate.id,
        source=candidate.source,
        title=candidate.title,
        url=candidate.url,
        summary=candidate.summary,
        image_url=candidate.image_url,
        published_at=candidate.published_at,
        discovered_at=candidate.discovered_at,
        hash=candidate.hash,
        metadata_json=json.dumps(candidate.metadata) if candidate.metadata else None,
        confidence=candidate.confidence,
        estado=candidate.estado.value,
    )


def _to_domain(model: NewsCandidateModel) -> NewsCandidate:
    # SQLite has no native timezone-aware timestamp type and silently drops
    # tzinfo on round trip (Postgres does not) — same fix already applied in
    # `database.repositories.publication_request_repository`.
    published_at = model.published_at
    if published_at is not None and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    discovered_at = model.discovered_at
    if discovered_at.tzinfo is None:
        discovered_at = discovered_at.replace(tzinfo=UTC)
    return NewsCandidate(
        id=model.id,
        source=model.source,
        title=model.title,
        url=model.url,
        summary=model.summary,
        image_url=model.image_url,
        published_at=published_at,
        discovered_at=discovered_at,
        hash=model.hash,
        metadata=json.loads(model.metadata_json) if model.metadata_json is not None else {},
        confidence=model.confidence,
        estado=EstadoNewsCandidate(model.estado),
    )


class SqlAlchemyNewsCandidateRepository:
    """`NewsCandidateRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: NewsCandidate) -> None:
        """Persist `entity`, creating or updating it as needed."""
        self._session.merge(_to_model(entity))

    def get_by_id(self, id: str) -> NewsCandidate | None:
        """Return the `NewsCandidate` identified by `id`, or `None` if not found."""
        model = self._session.get(NewsCandidateModel, id)
        return _to_domain(model) if model is not None else None

    def exists(self, reference: str) -> bool:
        """Return whether a `NewsCandidate` with hash `reference` was already stored."""
        stmt = select(NewsCandidateModel.id).where(NewsCandidateModel.hash == reference)
        return self._session.execute(stmt).first() is not None

    def list_all(self) -> list[NewsCandidate]:
        """Return every persisted `NewsCandidate`."""
        models = self._session.execute(select(NewsCandidateModel)).scalars().all()
        return [_to_domain(model) for model in models]
