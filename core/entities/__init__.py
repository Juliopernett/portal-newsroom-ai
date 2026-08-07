"""Domain entities.

Plain, immutable dataclasses describing the shapes the domain works with
as content moves through the editorial pipeline — no behavior beyond
constructor validation, no infrastructure dependencies. Business logic
that spans more than one entity belongs in `core/services/`, not here.

Re-exported below so consumers can `from core.entities import
NewsCandidate` instead of reaching into the submodule.
"""

from __future__ import annotations

from core.entities.article import Article, ArticleStatus
from core.entities.client import Client, ClientType
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.editorial_task import EditorialTask, EditorialTaskStatus
from core.entities.news_candidate import NewsCandidate
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.entities.session import Session
from core.entities.source import Source
from core.entities.user import User

__all__ = [
    "Article",
    "ArticleStatus",
    "CanalPublicacion",
    "Client",
    "ClientType",
    "DestinoPublicacion",
    "EditorialTask",
    "EditorialTaskStatus",
    "EstadoDestino",
    "NewsCandidate",
    "Pauta",
    "PublicationRequest",
    "PublicationRequestStatus",
    "Session",
    "Source",
    "User",
]
