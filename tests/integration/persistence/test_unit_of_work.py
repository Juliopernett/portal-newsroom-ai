"""Integration tests: SqlAlchemyUnitOfWork transaction boundaries."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from core.entities.client import Client, ClientType
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion
from core.entities.publication_request import PublicationRequest
from database.unit_of_work import SqlAlchemyUnitOfWork


def _client(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def test_commit_persists_changes_visible_to_a_new_unit_of_work(
    session_factory: sessionmaker[Session],
) -> None:
    client = _client()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.clients.save(client)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.clients.get_by_id(client.id) == client


def test_exiting_without_commit_rolls_back(session_factory: sessionmaker[Session]) -> None:
    client = _client()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.clients.save(client)
        # no uow.commit() here — exiting the block must discard this

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.clients.get_by_id(client.id) is None


def test_an_exception_inside_the_block_rolls_back(
    session_factory: sessionmaker[Session],
) -> None:
    client = _client()

    with pytest.raises(RuntimeError), SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.clients.save(client)
        raise RuntimeError("boom")

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.clients.get_by_id(client.id) is None


def test_destinos_publicacion_is_wired_into_the_same_transaction(
    session_factory: sessionmaker[Session],
) -> None:
    """Two separate `with` blocks, matching how this happens in production: a
    PublicationRequest is created first (and committed) in its own request,
    a DestinoPublicacion is added to it later in a different one — never
    both as new FK-related rows in a single uncommitted transaction (see
    `tests/integration/persistence/test_destino_publicacion_repository.py`'s
    `_create_solicitud` docstring for what breaks if you do)."""
    solicitud = PublicationRequest(texto="Solicitud de ejemplo")
    destino = DestinoPublicacion(
        publication_request_id=solicitud.id, canal=CanalPublicacion.WORDPRESS
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.publication_requests.save(solicitud)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.destinos_publicacion.save(destino)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.destinos_publicacion.get_by_id(destino.id) == destino
