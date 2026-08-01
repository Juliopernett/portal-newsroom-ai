"""Integration tests: SqlAlchemyUnitOfWork transaction boundaries."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from core.entities.client import Client, ClientType
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
