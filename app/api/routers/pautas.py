"""Routes for Pauta.

`GET /pautas/{pauta_id}` is what "consultar el estado de las publicaciones
restantes" (Sprint 3D) actually is — it reuses
`core.services.pauta_service.PautaService`, already built and tested in
Sprint 3B, without any new domain logic.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it — **except**
`router_publico` (see below): `GET /{pauta_id}/informe-publico.pdf` is the
"Enviar por WhatsApp" share link, meant to be opened by the client, who
never logs in. It carries its own token-based guard instead of a session.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.api.dependencies import (
    get_current_user,
    get_media_storage,
    get_unit_of_work,
    hash_session_token,
)
from app.api.pdf_informe import generar_informe_pauta_pdf
from app.api.schemas.pauta import InformeLinkOut, PautaCreate, PautaOut
from config.settings import get_settings
from core.entities.informe_link import InformeLink
from core.entities.pauta import Pauta
from core.ports.media_storage import MediaStorage
from core.ports.unit_of_work import UnitOfWork
from core.services.pauta_service import PautaService
from core.services.reporte_service import construir_reporte_pauta

router = APIRouter(prefix="/pautas", tags=["pautas"], dependencies=[Depends(get_current_user)])
router_publico = APIRouter(prefix="/pautas", tags=["pautas"])

_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _to_out(pauta: Pauta, uow: UnitOfWork) -> PautaOut:
    solicitudes = uow.publication_requests.list_by_pauta_id(pauta.id)
    # Sprint 4A, Increment 4: destinos scoped per-solicitud, not
    # uow.destinos_publicacion.list_all() — this runs once per Pauta from
    # list_pautas' loop, and fetching every destino in the system on each
    # iteration would be far more wasteful than these targeted queries.
    destinos = [
        destino
        for solicitud in solicitudes
        for destino in uow.destinos_publicacion.list_by_publication_request_id(solicitud.id)
    ]
    service = PautaService()
    return PautaOut(
        id=pauta.id,
        client_id=pauta.client_id,
        fecha_inicio=pauta.fecha_inicio,
        fecha_fin=pauta.fecha_fin,
        publicaciones_contratadas=pauta.publicaciones_contratadas,
        valor_pagado=pauta.valor_pagado,
        fecha_pago=pauta.fecha_pago,
        saldo_pendiente=pauta.saldo_pendiente,
        fecha_registro=pauta.fecha_registro,
        observaciones=pauta.observaciones,
        publicaciones_consumidas=service.publicaciones_consumidas(pauta, solicitudes, destinos),
        publicaciones_restantes=service.publicaciones_restantes(pauta, solicitudes, destinos),
        vigente=service.esta_vigente(pauta),
        vencida=service.esta_vencida(pauta),
        cuota_agotada=service.cuota_agotada(pauta, solicitudes, destinos),
        peso_comercial=pauta.peso_comercial,
        tipo=pauta.tipo,
    )


@router.post("", response_model=PautaOut, status_code=201)
def create_pauta(payload: PautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)) -> PautaOut:
    """Register a new Pauta for an existing Client."""
    pauta = Pauta(**payload.model_dump())
    uow.pautas.save(pauta)
    uow.commit()
    return _to_out(pauta, uow)


@router.put("/{pauta_id}", response_model=PautaOut)
def update_pauta(
    pauta_id: str, payload: PautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PautaOut:
    """Replace an existing Pauta's editable fields (fecha_inicio, fecha_fin, ...).

    Same PUT-semantics discipline `app.api.routers.clients.update_client`
    already uses for `Client`: `Pauta` is immutable (`frozen=True`), so
    this builds a new instance via `dataclasses.replace`, which re-runs
    `__post_init__` validation. Added 2026-08-14 after a real data-entry
    mistake (a Pauta saved with the wrong fecha_fin) had no way to be
    corrected short of editing the database directly. `id` and
    `fecha_registro` (audit timestamp, never meant to be edited — see
    `Pauta`'s own docstring) are preserved; every other field is replaced
    wholesale from the payload, `client_id` included — the same wholesale
    replacement `Client` already allows.
    """
    existing = uow.pautas.get_by_id(pauta_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    updated = replace(existing, **payload.model_dump())
    uow.pautas.save(updated)
    uow.commit()
    return _to_out(updated, uow)


@router.get("/{pauta_id}", response_model=PautaOut)
def get_pauta(pauta_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> PautaOut:
    """Return a Pauta with its computed quota status."""
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    return _to_out(pauta, uow)


@router.get("", response_model=list[PautaOut])
def list_pautas(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[PautaOut]:
    """Return every Pauta with its computed quota status — the admin screen's data."""
    return [_to_out(pauta, uow) for pauta in uow.pautas.list_all()]


def _nombre_archivo_informe(pauta: Pauta, cliente_nombre: str | None) -> str:
    base = f"informe-{cliente_nombre or 'cliente'}-{pauta.fecha_inicio.isoformat()}"
    return _FILENAME_UNSAFE.sub("-", base).strip("-") + ".pdf"


def _generar_informe_pdf_response(
    pauta_id: str, uow: UnitOfWork, media_storage: MediaStorage
) -> Response:
    """Build the `informe.pdf` `Response` for one Pauta — the one place
    both `descargar_informe_pauta` (authenticated) and
    `descargar_informe_pauta_publico` (token-guarded) build it, so the two
    entry points can never drift in what they generate.

    Nothing is persisted, there is no "reportes" table — built on demand
    from current data every time. Reuses `construir_reporte_pauta` (pure
    aggregation over the exact same `PautaService`/`esta_completa` logic
    every other quota view already uses) and
    `app.api.pdf_informe.generar_informe_pauta_pdf` (rendering only, no
    domain logic of its own).
    """
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    cliente = uow.clients.get_by_id(pauta.client_id)
    solicitudes = uow.publication_requests.list_by_pauta_id(pauta_id)
    destinos = [
        destino
        for solicitud in solicitudes
        for destino in uow.destinos_publicacion.list_by_publication_request_id(solicitud.id)
    ]
    reporte = construir_reporte_pauta(pauta, solicitudes, destinos, cliente, PautaService())

    identidad = uow.identidad_comercial.get()
    logo_bytes: bytes | None = None
    if identidad is not None and identidad.logo_storage_key is not None:
        try:
            logo_bytes = media_storage.leer(identidad.logo_storage_key)
        except FileNotFoundError:
            logo_bytes = None

    pdf_bytes = generar_informe_pauta_pdf(reporte, identidad, logo_bytes)
    filename = _nombre_archivo_informe(pauta, cliente.nombre if cliente else None)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{pauta_id}/informe.pdf")
def descargar_informe_pauta(
    pauta_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Generate and download the client-facing closing report for one Pauta
    (Sprint — informe de cierre de contrato). See `_generar_informe_pdf_response`."""
    return _generar_informe_pdf_response(pauta_id, uow, media_storage)


@router.post("/{pauta_id}/informe-link", response_model=InformeLinkOut)
def crear_informe_link(
    pauta_id: str,
    request: Request,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> InformeLinkOut:
    """Mint a fresh, time-limited share link to this Pauta's informe —
    "Enviar por WhatsApp" on the Contratos card.

    Every click gets its own token (never reused), so there is nothing to
    invalidate on the previous one — it simply expires on its own schedule
    (`settings.informe_link_ttl_dias`, default 15 días). Only the SHA-256
    hash is stored (`hash_session_token` — the same generic helper
    `core.entities.session.Session` uses, not session-specific despite the
    name), same discipline as a login session: a leaked database row alone
    can't be replayed as a working link.
    """
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")

    settings = get_settings()
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.informe_link_ttl_dias)
    link = InformeLink(
        pauta_id=pauta_id, token_hash=hash_session_token(token), expires_at=expires_at
    )
    uow.informe_links.save(link)
    uow.commit()

    # Railway terminates TLS in front of uvicorn (no --proxy-headers), so
    # `request.url.scheme` alone would report `http` in production — force
    # `https` there instead of trusting it, same conditional
    # `app.api.routers.auth._set_session_cookie` already applies to the
    # session cookie's `secure` flag.
    scheme = "https" if settings.environment == "production" else request.url.scheme
    url = f"{scheme}://{request.url.netloc}/pautas/{pauta_id}/informe-publico.pdf?token={token}"
    return InformeLinkOut(url=url, expira_en=expires_at)


@router_publico.get("/{pauta_id}/informe-publico.pdf")
def descargar_informe_pauta_publico(
    pauta_id: str,
    token: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """The unauthenticated side of `crear_informe_link` — what a client
    actually opens from WhatsApp. `404` for a missing/expired/mismatched
    token, same as a genuinely-missing Pauta, so a guess reveals nothing
    either way."""
    link = uow.informe_links.get_by_token_hash(hash_session_token(token))
    if link is None or link.pauta_id != pauta_id or link.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=404, detail="Enlace no válido o expirado")
    return _generar_informe_pdf_response(pauta_id, uow, media_storage)
