"""SQLAlchemy adapter for `core.ports.informe_link_repository.InformeLinkRepository`.

Translates between `core.entities.informe_link.InformeLink` (domain) and
`database.models.informe_link.InformeLinkModel` (ORM). The domain never
sees this module.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.informe_link import InformeLink
from database.models.informe_link import InformeLinkModel


def _to_model(link: InformeLink) -> InformeLinkModel:
    return InformeLinkModel(
        id=link.id,
        pauta_id=link.pauta_id,
        token_hash=link.token_hash,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


def _aware(value: datetime) -> datetime:
    """Re-attach UTC tzinfo SQLite drops on round trip (Postgres does not)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_domain(model: InformeLinkModel) -> InformeLink:
    return InformeLink(
        id=model.id,
        pauta_id=model.pauta_id,
        token_hash=model.token_hash,
        created_at=_aware(model.created_at),
        expires_at=_aware(model.expires_at),
    )


class SqlAlchemyInformeLinkRepository:
    """`InformeLinkRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: SqlAlchemySession) -> None:
        self._session = session

    def save(self, link: InformeLink) -> None:
        """Persist `link`, creating or updating it as needed."""
        self._session.merge(_to_model(link))

    def get_by_token_hash(self, token_hash: str) -> InformeLink | None:
        """Return the `InformeLink` identified by `token_hash`, or `None`."""
        stmt = select(InformeLinkModel).where(InformeLinkModel.token_hash == token_hash)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_domain(model) if model is not None else None
