"""Integration tests: SqlAlchemyPublicationRequestRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from core.entities.publication_request import (
    EstadoPreparacionIA,
    PublicationRequest,
    PublicationRequestStatus,
)
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)


def _create_pauta(session: Session, **overrides: object) -> Pauta:
    """Persist a Client and a Pauta for it, so FK-constrained tests have a real parent."""
    client = Client(nombre="Silvestre Dangond", tipo=ClientType.ARTISTA, telefono="+573001112233")
    SqlAlchemyClientRepository(session).save(client)

    defaults: dict[str, object] = {
        "client_id": client.id,
        "fecha_inicio": date(2026, 7, 30),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000.00"),
        "fecha_pago": date(2026, 7, 30),
    }
    defaults.update(overrides)
    pauta = Pauta(**defaults)
    SqlAlchemyPautaRepository(session).save(pauta)
    return pauta


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {"texto": "Solicitud de ejemplo"}
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_save_and_get_by_id_round_trips_a_linked_request(session: Session) -> None:
    pauta = _create_pauta(session)
    repository = SqlAlchemyPublicationRequestRepository(session)
    solicitud = _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.ACEPTADA)

    repository.save(solicitud)
    session.commit()

    assert repository.get_by_id(solicitud.id) == solicitud


def test_save_and_get_by_id_round_trips_a_request_without_a_pauta(session: Session) -> None:
    """Sprint 3B.1: a RECIBIDA request can exist with pauta_id=None."""
    repository = SqlAlchemyPublicationRequestRepository(session)
    solicitud = _solicitud(pauta_id=None)

    repository.save(solicitud)
    session.commit()

    recuperada = repository.get_by_id(solicitud.id)
    assert recuperada == solicitud
    assert recuperada is not None
    assert recuperada.pauta_id is None


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyPublicationRequestRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_list_by_pauta_id_returns_only_requests_linked_to_that_pauta(session: Session) -> None:
    esta_pauta = _create_pauta(session)
    otra_pauta = _create_pauta(session)
    repository = SqlAlchemyPublicationRequestRepository(session)
    de_esta_pauta = _solicitud(pauta_id=esta_pauta.id)
    de_otra_pauta = _solicitud(pauta_id=otra_pauta.id)
    sin_pauta = _solicitud(pauta_id=None)
    for solicitud in (de_esta_pauta, de_otra_pauta, sin_pauta):
        repository.save(solicitud)
    session.commit()

    resultado = repository.list_by_pauta_id(esta_pauta.id)

    assert [solicitud.id for solicitud in resultado] == [de_esta_pauta.id]


def test_list_all_returns_every_request(session: Session) -> None:
    pauta = _create_pauta(session)
    repository = SqlAlchemyPublicationRequestRepository(session)
    recibida = _solicitud(pauta_id=pauta.id)
    aceptada = _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.ACEPTADA)
    repository.save(recibida)
    repository.save(aceptada)
    session.commit()

    resultado = repository.list_all()

    assert {solicitud.id for solicitud in resultado} == {recibida.id, aceptada.id}


def test_save_and_get_by_id_round_trips_titulo_and_fecha_cierre(session: Session) -> None:
    repository = SqlAlchemyPublicationRequestRepository(session)
    solicitud = _solicitud(
        titulo="Lanzamiento del sencillo",
        fecha_cierre=datetime(2026, 8, 6, 15, 0, tzinfo=UTC),
    )

    repository.save(solicitud)
    session.commit()

    recuperada = repository.get_by_id(solicitud.id)
    assert recuperada == solicitud
    assert recuperada is not None
    assert recuperada.titulo == "Lanzamiento del sencillo"
    assert recuperada.fecha_cierre is not None


def test_save_and_get_by_id_round_trips_editorial_fields(session: Session) -> None:
    repository = SqlAlchemyPublicationRequestRepository(session)
    solicitud = _solicitud(
        contenido_editorial="Cuerpo reescrito",
        entradilla_editorial="Entradilla",
        titulo_editorial="Titular IA",
        categoria_editorial="Noticias",
        etiquetas_editorial=("vallenato", "lanzamiento"),
        slug_editorial="titular-ia",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )

    repository.save(solicitud)
    session.commit()

    recuperada = repository.get_by_id(solicitud.id)
    assert recuperada == solicitud
    assert recuperada is not None
    assert recuperada.contenido_editorial == "Cuerpo reescrito"
    assert recuperada.etiquetas_editorial == ("vallenato", "lanzamiento")
    assert recuperada.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO


def test_save_and_get_by_id_defaults_preparacion_ia_estado_to_pendiente(session: Session) -> None:
    repository = SqlAlchemyPublicationRequestRepository(session)
    solicitud = _solicitud()

    repository.save(solicitud)
    session.commit()

    recuperada = repository.get_by_id(solicitud.id)
    assert recuperada is not None
    assert recuperada.preparacion_ia_estado == EstadoPreparacionIA.PENDIENTE
    assert recuperada.contenido_editorial is None
    assert recuperada.etiquetas_editorial is None


def test_list_all_filters_by_estado(session: Session) -> None:
    pauta = _create_pauta(session)
    repository = SqlAlchemyPublicationRequestRepository(session)
    recibida = _solicitud(pauta_id=pauta.id)
    aceptada = _solicitud(pauta_id=pauta.id, estado=PublicationRequestStatus.ACEPTADA)
    repository.save(recibida)
    repository.save(aceptada)
    session.commit()

    resultado = repository.list_all(estado=PublicationRequestStatus.RECIBIDA)

    assert [solicitud.id for solicitud in resultado] == [recibida.id]
