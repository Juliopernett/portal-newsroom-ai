"""Concrete repositories.

Each module here implements one `core/ports/*_repository.py` Protocol on
top of SQLAlchemy, translating between a domain entity and its ORM model
(`database/models/`). Constructed with an already-open `Session` — never
opens one itself, see `database.unit_of_work.SqlAlchemyUnitOfWork`.
"""

from __future__ import annotations

from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.destino_publicacion_repository import (
    SqlAlchemyDestinoPublicacionRepository,
)
from database.repositories.media_asset_repository import SqlAlchemyMediaAssetRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)
from database.repositories.session_repository import SqlAlchemySessionRepository
from database.repositories.user_repository import SqlAlchemyUserRepository

__all__ = [
    "SqlAlchemyClientRepository",
    "SqlAlchemyDestinoPublicacionRepository",
    "SqlAlchemyMediaAssetRepository",
    "SqlAlchemyPautaRepository",
    "SqlAlchemyPublicationRequestRepository",
    "SqlAlchemySessionRepository",
    "SqlAlchemyUserRepository",
]
