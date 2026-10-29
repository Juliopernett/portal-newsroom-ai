"""Builds the `ContentSource` adapter that matches a `Source`'s `type`.

Sprint Fuentes (2026-10-29). The one place that knows which adapter serves
which source type, so `core.services.source_scan_service` stays free of
concrete adapters. New kinds of source (e.g. Instagram) are added here.
"""

from __future__ import annotations

from agents.radar.rss_content_source import RssContentSource
from core.entities.source import Source
from core.ports.content_source import ContentSource, ContentSourceError

TIPOS_SOPORTADOS = ("rss",)


def crear_adaptador(source: Source) -> ContentSource:
    """Return the adapter for `source`, or raise `ContentSourceError` for an unknown type."""
    if source.type == "rss":
        return RssContentSource(source, validar_url=True)
    raise ContentSourceError(f"Tipo de fuente no soportado: '{source.type}'")
