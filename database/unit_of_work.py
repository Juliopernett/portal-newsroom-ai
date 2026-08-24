"""SQLAlchemy adapter for `core.ports.unit_of_work.UnitOfWork`.

Owns a single `Session` for the lifetime of the `with` block, wires the
three concrete repositories to it, and commits/rolls back that one
session — the transaction boundary is the `with` block, nothing else.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from core.ports.unit_of_work import UnitOfWork
from database.repositories.ai_configuracion_repository import (
    SqlAlchemyAIConfiguracionRepository,
)
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.destino_publicacion_repository import (
    SqlAlchemyDestinoPublicacionRepository,
)
from database.repositories.gasto_repository import SqlAlchemyGastoRepository
from database.repositories.identidad_comercial_repository import (
    SqlAlchemyIdentidadComercialRepository,
)
from database.repositories.informe_link_repository import SqlAlchemyInformeLinkRepository
from database.repositories.media_asset_repository import SqlAlchemyMediaAssetRepository
from database.repositories.otro_ingreso_repository import SqlAlchemyOtroIngresoRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository
from database.repositories.plan_pauta_repository import SqlAlchemyPlanPautaRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)
from database.repositories.session_repository import SqlAlchemySessionRepository
from database.repositories.user_repository import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Groups `Client`/`Pauta`/`PublicationRequest`/`DestinoPublicacion`/
    `MediaAsset`/`Gasto`/`OtroIngreso`/`IdentidadComercial`/`InformeLink`/
    `User`/`Session` repos in one transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.clients = SqlAlchemyClientRepository(self._session)
        self.pautas = SqlAlchemyPautaRepository(self._session)
        self.planes_pauta = SqlAlchemyPlanPautaRepository(self._session)
        self.publication_requests = SqlAlchemyPublicationRequestRepository(self._session)
        self.destinos_publicacion = SqlAlchemyDestinoPublicacionRepository(self._session)
        self.media_assets = SqlAlchemyMediaAssetRepository(self._session)
        self.gastos = SqlAlchemyGastoRepository(self._session)
        self.otros_ingresos = SqlAlchemyOtroIngresoRepository(self._session)
        self.identidad_comercial = SqlAlchemyIdentidadComercialRepository(self._session)
        self.ai_configuracion = SqlAlchemyAIConfiguracionRepository(self._session)
        self.informe_links = SqlAlchemyInformeLinkRepository(self._session)
        self.users = SqlAlchemyUserRepository(self._session)
        self.sessions = SqlAlchemySessionRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        super().__exit__(exc_type, exc_value, traceback)
        assert self._session is not None
        self._session.close()
        self._session = None

    def commit(self) -> None:
        """Commit the current session's transaction."""
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        """Roll back the current session's transaction."""
        assert self._session is not None
        self._session.rollback()
