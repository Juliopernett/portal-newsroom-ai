"""Domain service: MediaAsset upload validation and the purge condition.

Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md). A
`MediaAsset` has no lifecycle states of its own — its only transition is
"gone" (purged or manually deleted), so unlike
`core.services.destino_publicacion_service` there is nothing here that
returns a modified copy of the entity; every function is a pure
predicate or a pure builder.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.entities.media_asset import MediaAssetType
from core.entities.publication_request import PublicationRequest

# Closed allow-list, not `startswith("image/")` — that would also accept
# `image/svg+xml`, which is XML, not a raster image: a SVG can carry
# `<script>`/`onload`, and a route that serves it back with
# `Content-Disposition: inline` (`descargar_media` here, and
# `identidad_comercial.descargar_logo`, which reuses this same set) would
# render — and run — it in the browser at this same origin instead of
# downloading as a file (security audit 2026-08-20, findings H1/M2).
TIPOS_IMAGEN_PERMITIDOS = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
_TIPOS_VIDEO_PREFIX = "video/"


def determinar_tipo(content_type: str) -> MediaAssetType:
    """Return the `MediaAssetType` for `content_type`, or raise `ValueError`.

    Audio is deliberately unsupported (ADR-007 Decision 1 — not part of
    what the business asked for). The caller (the upload route) never
    trusts a client-supplied `tipo` directly — it's always derived from
    the file's own MIME type.
    """
    if content_type in TIPOS_IMAGEN_PERMITIDOS:
        return MediaAssetType.IMAGEN
    if content_type.startswith(_TIPOS_VIDEO_PREFIX):
        return MediaAssetType.VIDEO
    raise ValueError(f"content_type no soportado: {content_type!r} (solo imagen o video)")


def validar_tamano(
    tipo: MediaAssetType, tamano_bytes: int, *, max_bytes_imagen: int, max_bytes_video: int
) -> None:
    """Raise `ValueError` if `tamano_bytes` exceeds the configured limit for `tipo`."""
    limite = max_bytes_imagen if tipo is MediaAssetType.IMAGEN else max_bytes_video
    if tamano_bytes > limite:
        raise ValueError(
            f"el archivo pesa {tamano_bytes} bytes, el máximo para {tipo.value} es {limite} bytes"
        )


def construir_storage_key(publication_request_id: str, media_id: str) -> str:
    """Return the opaque storage key for one MediaAsset.

    Built only from the solicitud's and the media asset's own ids — never
    from the uploaded filename (`nombre_archivo`), so a crafted filename
    can never influence where the file is stored (ADR-007 Decision 1).
    """
    return f"{publication_request_id}/{media_id}"


def es_purgable(solicitud: PublicationRequest, *, retencion_dias: int, ahora: datetime) -> bool:
    """Return whether `solicitud`'s media attachments are due for purge.

    `True` only once the request is complete (`fecha_cierre` set) and
    `retencion_dias` have passed since that moment — a request still open
    never purges its media, no matter how long it has been pending (see
    ADR-007 Decision 3).
    """
    if solicitud.fecha_cierre is None:
        return False
    return ahora >= solicitud.fecha_cierre + timedelta(days=retencion_dias)
