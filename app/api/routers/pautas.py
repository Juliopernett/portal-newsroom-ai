"""Routes for Pauta.

`GET /pautas/{pauta_id}` is what "consultar el estado de las publicaciones
restantes" (Sprint 3D) actually is — it reuses
`core.services.pauta_service.PautaService`, already built and tested in
Sprint 3B, without any new domain logic.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it — **except**
`router_publico` (see below): `GET /{pauta_id}/informe-publico.pdf` and
`GET /{pauta_id}/contrato-publico.pdf` are the "Enviar al cliente" share
links, meant to be opened by the client, who never logs in. They carry
their own token-based guard instead of a session.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.api.dependencies import (
    get_current_user,
    get_media_storage,
    get_social_media_reader,
    get_unit_of_work,
    hash_session_token,
    limit_public_downloads,
)
from app.api.pdf_contrato import generar_contrato_pauta_pdf
from app.api.pdf_informe import generar_informe_pauta_pdf
from app.api.schemas.metricas import (
    FilaMetricaOut,
    MetricasPautaOut,
    MetricasPostOut,
    ResumenMetricasOut,
)
from app.api.schemas.pauta import InformeLinkOut, PautaCreate, PautaOut
from config.settings import get_settings
from core.entities.destino_publicacion import CanalPublicacion, EstadoDestino
from core.entities.informe_link import InformeLink
from core.entities.metrica_publicacion import MetricaPublicacion, MetricasPost
from core.entities.pauta import Pauta
from core.ports.media_storage import MediaStorage
from core.ports.social_media_reader import SocialMediaReader
from core.ports.unit_of_work import UnitOfWork
from core.services.metricas_service import FilaMetrica, resumir
from core.services.pauta_service import PautaService
from core.services.reporte_service import construir_reporte_pauta

router = APIRouter(prefix="/pautas", tags=["pautas"], dependencies=[Depends(get_current_user)])
router_publico = APIRouter(
    prefix="/pautas", tags=["pautas"], dependencies=[Depends(limit_public_downloads)]
)

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
        incluye_metricas=pauta.incluye_metricas,
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


def _nombre_archivo(prefijo: str, pauta: Pauta, cliente_nombre: str | None) -> str:
    base = f"{prefijo}-{cliente_nombre or 'cliente'}-{pauta.fecha_inicio.isoformat()}"
    return _FILENAME_UNSAFE.sub("-", base).strip("-") + ".pdf"


def _logo_bytes(uow: UnitOfWork, media_storage: MediaStorage) -> bytes | None:
    """Read the identidad comercial's logo bytes, or `None` when there is no
    identidad, no logo configured, or the stored file is missing."""
    identidad = uow.identidad_comercial.get()
    if identidad is None or identidad.logo_storage_key is None:
        return None
    try:
        return media_storage.leer(identidad.logo_storage_key)
    except FileNotFoundError:
        return None


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    metricas = None
    if pauta.incluye_metricas:  # opt-in per contract: never shown otherwise
        filas = _filas_metricas(pauta_id, uow)
        metricas = (resumir(filas), filas)
    pdf_bytes = generar_informe_pauta_pdf(
        reporte, identidad, _logo_bytes(uow, media_storage), metricas
    )
    filename = _nombre_archivo("informe", pauta, cliente.nombre if cliente else None)
    return _pdf_response(pdf_bytes, filename)


def _generar_contrato_pdf_response(
    pauta_id: str, uow: UnitOfWork, media_storage: MediaStorage
) -> Response:
    """Build the `contrato.pdf` `Response` for one Pauta — shared by
    `descargar_contrato_pauta` (authenticated) and
    `descargar_contrato_pauta_publico` (token-guarded), the same way
    `_generar_informe_pdf_response` is, so the two entry points can never
    drift in what they generate.

    Contract terms only — no `construir_reporte_pauta`, no `PautaService`:
    this document is meant to be sent when the pauta is about to start,
    before there is any publication history to aggregate.
    """
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    cliente = uow.clients.get_by_id(pauta.client_id)
    identidad = uow.identidad_comercial.get()
    pdf_bytes = generar_contrato_pauta_pdf(
        pauta, cliente, identidad, _logo_bytes(uow, media_storage)
    )
    filename = _nombre_archivo("contrato", pauta, cliente.nombre if cliente else None)
    return _pdf_response(pdf_bytes, filename)


@router.get("/{pauta_id}/informe.pdf")
def descargar_informe_pauta(
    pauta_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Generate and download the client-facing closing report for one Pauta
    (Sprint — informe de cierre de contrato). See `_generar_informe_pdf_response`."""
    return _generar_informe_pdf_response(pauta_id, uow, media_storage)


_CANALES_SOCIALES = (CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM)


def _filas_metricas(pauta_id: str, uow: UnitOfWork) -> list[FilaMetrica]:
    """Every published Facebook/Instagram post of this Pauta + its last capture."""
    pares = []
    for solicitud in uow.publication_requests.list_by_pauta_id(pauta_id):
        for destino in uow.destinos_publicacion.list_by_publication_request_id(solicitud.id):
            if destino.canal in _CANALES_SOCIALES and destino.estado is EstadoDestino.PUBLICADO:
                pares.append((solicitud, destino))
    capturas = {
        m.destino_id: m
        for m in uow.metricas_publicacion.list_by_destino_ids(d.id for _, d in pares)
    }
    return [
        FilaMetrica(
            destino_id=destino.id,
            solicitud_id=solicitud.id,
            titulo=((solicitud.titulo or solicitud.texto or "").strip()[:80]) or "(sin título)",
            canal=destino.canal,
            url=destino.url_publicacion,
            tiene_meta_post_id=destino.meta_post_id is not None,
            metrica=capturas.get(destino.id),
        )
        for solicitud, destino in pares
    ]


def _metricas_out(
    pauta: Pauta, filas: list[FilaMetrica], errores: list[str] | None = None
) -> MetricasPautaOut:
    return MetricasPautaOut(
        incluye_metricas=pauta.incluye_metricas,
        resumen=ResumenMetricasOut(**_resumen_dict(resumir(filas))),
        filas=[
            FilaMetricaOut(
                destino_id=f.destino_id,
                solicitud_id=f.solicitud_id,
                titulo=f.titulo,
                canal=f.canal,
                url=f.url,
                tiene_meta_post_id=f.tiene_meta_post_id,
                capturado_en=f.metrica.capturado_en if f.metrica else None,
                metricas=(
                    MetricasPostOut(
                        alcance=f.metrica.metricas.alcance,
                        vistas=f.metrica.metricas.vistas,
                        reacciones=f.metrica.metricas.reacciones,
                        comentarios=f.metrica.metricas.comentarios,
                        compartidos=f.metrica.metricas.compartidos,
                        guardados=f.metrica.metricas.guardados,
                        interacciones=f.metrica.metricas.interacciones,
                    )
                    if f.metrica
                    else None
                ),
            )
            for f in filas
        ],
        errores=errores or [],
    )


def _resumen_dict(resumen: object) -> dict[str, int | None]:
    return {k: getattr(resumen, k) for k in ResumenMetricasOut.model_fields}


@router.get("/{pauta_id}/metricas", response_model=MetricasPautaOut)
def ver_metricas_pauta(
    pauta_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> MetricasPautaOut:
    """Internal preview of the informe's metrics block — what the client WOULD
    see — so the operator can decide per contract whether to include it."""
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    return _metricas_out(pauta, _filas_metricas(pauta_id, uow))


@router.post("/{pauta_id}/metricas/actualizar", response_model=MetricasPautaOut)
def actualizar_metricas_pauta(
    pauta_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    reader: SocialMediaReader = Depends(get_social_media_reader),
) -> MetricasPautaOut:
    """Pull fresh numbers from Meta for every published post of this Pauta in
    ONE request (bulk by design), and save them. A post that fails is
    reported in `errores` without losing the others. Works whether or not the
    contract includes metrics in its informe."""
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    errores: list[str] = []
    for fila in _filas_metricas(pauta_id, uow):
        if not fila.tiene_meta_post_id:
            continue
        destino = next(
            d
            for d in uow.destinos_publicacion.list_by_publication_request_id(fila.solicitud_id)
            if d.id == fila.destino_id
        )
        try:
            metricas: MetricasPost = reader.metricas_post(fila.canal, destino.meta_post_id or "")
        except requests.RequestException:
            errores.append(f"{fila.titulo} ({fila.canal.value}): no se pudo consultar Meta")
            continue
        uow.metricas_publicacion.save(
            MetricaPublicacion(destino_id=fila.destino_id, canal=fila.canal, metricas=metricas)
        )
    uow.commit()
    return _metricas_out(pauta, _filas_metricas(pauta_id, uow), errores)


def _mint_share_link(
    pauta_id: str, documento_publico: str, request: Request, uow: UnitOfWork
) -> InformeLinkOut:
    """Mint a fresh, time-limited share link to one of this Pauta's
    client-facing PDFs — `documento_publico` is the public route segment
    (`informe-publico.pdf` or `contrato-publico.pdf`).

    Every click gets its own token (never reused), so there is nothing to
    invalidate on the previous one — it simply expires on its own schedule
    (`settings.informe_link_ttl_dias`, default 15 días). Only the SHA-256
    hash is stored (`hash_session_token` — the same generic helper
    `core.entities.session.Session` uses, not session-specific despite the
    name), same discipline as a login session: a leaked database row alone
    can't be replayed as a working link. The token scopes access to the
    Pauta, not to one document — informe and contrato are the same
    client's own PDFs shared with that same client.
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
    url = f"{scheme}://{request.url.netloc}/pautas/{pauta_id}/{documento_publico}?token={token}"
    return InformeLinkOut(url=url, expira_en=expires_at)


def _validar_token_publico(pauta_id: str, token: str, uow: UnitOfWork) -> None:
    """Raise `404` for a missing/expired/mismatched token, same as a
    genuinely-missing Pauta, so a guess reveals nothing either way."""
    link = uow.informe_links.get_by_token_hash(hash_session_token(token))
    if link is None or link.pauta_id != pauta_id or link.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=404, detail="Enlace no válido o expirado")


@router.post("/{pauta_id}/informe-link", response_model=InformeLinkOut)
def crear_informe_link(
    pauta_id: str,
    request: Request,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> InformeLinkOut:
    """Mint a share link to this Pauta's informe — "Enviar al cliente" on
    the Contratos card. See `_mint_share_link`."""
    return _mint_share_link(pauta_id, "informe-publico.pdf", request, uow)


@router_publico.get("/{pauta_id}/informe-publico.pdf")
def descargar_informe_pauta_publico(
    pauta_id: str,
    token: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """The unauthenticated side of `crear_informe_link` — what a client
    actually opens from WhatsApp."""
    _validar_token_publico(pauta_id, token, uow)
    return _generar_informe_pdf_response(pauta_id, uow, media_storage)


@router.get("/{pauta_id}/contrato.pdf")
def descargar_contrato_pauta(
    pauta_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Generate and download the client-facing contract terms for one Pauta —
    the document sent when the pauta is about to start. See
    `_generar_contrato_pdf_response`."""
    return _generar_contrato_pdf_response(pauta_id, uow, media_storage)


@router.post("/{pauta_id}/contrato-link", response_model=InformeLinkOut)
def crear_contrato_link(
    pauta_id: str,
    request: Request,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> InformeLinkOut:
    """Mint a share link to this Pauta's contrato — "Enviar contrato al
    cliente" on the Contratos card. See `_mint_share_link`."""
    return _mint_share_link(pauta_id, "contrato-publico.pdf", request, uow)


@router_publico.get("/{pauta_id}/contrato-publico.pdf")
def descargar_contrato_pauta_publico(
    pauta_id: str,
    token: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """The unauthenticated side of `crear_contrato_link` — what a client
    actually opens from WhatsApp."""
    _validar_token_publico(pauta_id, token, uow)
    return _generar_contrato_pdf_response(pauta_id, uow, media_storage)
