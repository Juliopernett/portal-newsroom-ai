"""Integration test: PautaService fed by data retrieved from real repositories.

Sprint 3B proved PautaService against in-memory fakes. This closes the
loop the domain review flagged before Sprint 3C: the exact same service,
unmodified, computing the exact same answers from data that made a full
round trip through SQLAlchemy.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.pauta_service import PautaService
from core.services.publication_request_service import mark_as_published
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)


def test_pauta_service_computes_quota_from_persisted_publication_requests(
    session: Session,
) -> None:
    clients = SqlAlchemyClientRepository(session)
    pautas = SqlAlchemyPautaRepository(session)
    solicitudes = SqlAlchemyPublicationRequestRepository(session)

    client = Client(nombre="Silvestre Dangond", tipo=ClientType.ARTISTA, telefono="+573001112233")
    clients.save(client)

    pauta = Pauta(
        client_id=client.id,
        fecha_inicio=date(2026, 7, 30),
        fecha_fin=date(2026, 8, 30),
        publicaciones_contratadas=10,
        valor_pagado=Decimal("500000.00"),
        fecha_pago=date(2026, 7, 30),
    )
    pautas.save(pauta)

    primera = PublicationRequest(pauta_id=pauta.id, texto="Anuncio de nueva canción")
    segunda = PublicationRequest(pauta_id=pauta.id, texto="Fecha del próximo concierto")
    tercera = PublicationRequest(pauta_id=pauta.id, texto="Entrevista exclusiva")
    for solicitud in (mark_as_published(primera), mark_as_published(segunda), tercera):
        solicitudes.save(solicitud)
    session.commit()

    solicitudes_de_la_pauta = solicitudes.list_by_pauta_id(pauta.id)
    service = PautaService(clock=lambda: date(2026, 8, 1))

    assert service.publicaciones_restantes(pauta, solicitudes_de_la_pauta) == 8
    assert service.esta_vigente(pauta) is True

    todas_las_pautas = pautas.list_all()
    assert service.pautas_por_vencer(todas_las_pautas, dentro_de_dias=60) == [pauta]
