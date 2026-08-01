"""SQLAlchemy adapter for `core.ports.client_repository.ClientRepository`.

Translates between `core.entities.client.Client` (domain, immutable,
SQLAlchemy-unaware) and `database.models.client.ClientModel` (ORM). The
domain never sees this module.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.client import Client, ClientType
from database.models.client import ClientModel


def _to_model(client: Client) -> ClientModel:
    return ClientModel(
        id=client.id,
        nombre=client.nombre,
        tipo=client.tipo.value,
        telefono=client.telefono,
        instagram=client.instagram,
        observaciones=client.observaciones,
    )


def _to_domain(model: ClientModel) -> Client:
    return Client(
        id=model.id,
        nombre=model.nombre,
        tipo=ClientType(model.tipo),
        telefono=model.telefono,
        instagram=model.instagram,
        observaciones=model.observaciones,
    )


class SqlAlchemyClientRepository:
    """`ClientRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, client: Client) -> None:
        """Persist `client`, creating or updating it as needed."""
        self._session.merge(_to_model(client))

    def get_by_id(self, id: str) -> Client | None:
        """Return the `Client` identified by `id`, or `None` if not found."""
        model = self._session.get(ClientModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[Client]:
        """Return every `Client` — what the client picker/list needs."""
        models = self._session.execute(select(ClientModel)).scalars().all()
        return [_to_domain(model) for model in models]
