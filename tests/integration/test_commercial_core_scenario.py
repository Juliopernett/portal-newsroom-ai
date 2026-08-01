"""Integration test: the Excel-replacement scenario for Commercial Core MVP.

A client buys a Pauta of 10 publications, three requests come in, two get
published, and PautaService reports the remaining quota, expiration and
exhaustion — all computed from the entities themselves, nothing stored.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.pauta_service import PautaService
from core.services.publication_request_service import mark_as_published


def test_pauta_quota_and_validity_are_tracked_without_a_spreadsheet() -> None:
    client = Client(
        nombre="Silvestre Dangond",
        tipo=ClientType.ARTISTA,
        telefono="+573001112233",
    )
    pauta = Pauta(
        client_id=client.id,
        fecha_inicio=date(2026, 7, 30),
        fecha_fin=date(2026, 8, 30),
        publicaciones_contratadas=10,
        valor_pagado=Decimal("500000"),
        fecha_pago=date(2026, 7, 30),
    )

    primera = PublicationRequest(pauta_id=pauta.id, texto="Anuncio de nueva canción")
    segunda = PublicationRequest(pauta_id=pauta.id, texto="Fecha del próximo concierto")
    tercera = PublicationRequest(pauta_id=pauta.id, texto="Entrevista exclusiva")

    solicitudes = [mark_as_published(primera), mark_as_published(segunda), tercera]

    service = PautaService(clock=lambda: date(2026, 8, 1))
    assert service.publicaciones_restantes(pauta, solicitudes) == 8

    despues_del_vencimiento = PautaService(clock=lambda: pauta.fecha_fin + timedelta(days=1))
    assert despues_del_vencimiento.esta_vencida(pauta) is True
    assert despues_del_vencimiento.esta_vigente(pauta) is False

    diez_publicadas = [
        mark_as_published(PublicationRequest(pauta_id=pauta.id, texto=f"Solicitud {n}"))
        for n in range(pauta.publicaciones_contratadas)
    ]
    assert service.cuota_agotada(pauta, diez_publicadas) is True
