"""Domain service: heuristic match score between a solicitud and a Meta post.

2026-08-20, "conciliación inteligente de publicaciones en Meta" — helps an
operator find the right post in the picker faster; never decides for
them. `app.api.routers.social` only ever uses this score to *sort*
candidates — nothing here relates a post to a solicitud automatically,
and nothing in this module touches persistence. Deliberately simple,
explainable rules — no generative AI, per the sprint's own scope
("No quiero introducir IA generativa todavía").
"""

from __future__ import annotations

import re
from datetime import datetime

_TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)
_MIN_TOKEN_LEN = 3
_VENTANA_FECHA_DIAS = 7.0

_PESO_TEXTO = 0.4
_PESO_CLIENTE = 0.4
_PESO_FECHA = 0.2


def _tokenizar(texto: str) -> set[str]:
    """Lowercase word tokens, `_MIN_TOKEN_LEN`+ chars — short enough to drop
    most Spanish stopwords ("de", "la", "en", "su", ...) without a stopword
    list, per the sprint's "reglas simples" scope."""
    return {t for t in _TOKEN_RE.findall(texto.lower()) if len(t) >= _MIN_TOKEN_LEN}


def _score_texto(solicitud_tokens: set[str], post_tokens: set[str]) -> float:
    """Overlap coefficient, not Jaccard — a short caption fully contained in
    a longer solicitud texto should still score high, not get diluted by
    the size difference the way Jaccard's union would."""
    if not solicitud_tokens or not post_tokens:
        return 0.0
    interseccion = solicitud_tokens & post_tokens
    return len(interseccion) / min(len(solicitud_tokens), len(post_tokens))


def _score_cliente(cliente_nombre: str | None, post_tokens: set[str]) -> float:
    """Fraction of the client's own name tokens found in the post's caption
    — real captions very often name or tag the artist directly, so this is
    usually the strongest single signal available."""
    if not cliente_nombre:
        return 0.0
    nombre_tokens = _tokenizar(cliente_nombre)
    if not nombre_tokens:
        return 0.0
    return len(nombre_tokens & post_tokens) / len(nombre_tokens)


def _score_fecha(fecha_solicitud: datetime, fecha_post: datetime) -> float:
    """Linear decay to 0 over `_VENTANA_FECHA_DIAS` — publishing rarely
    happens same-day (see the posts-recientes picker's own design, which
    deliberately does not hard-filter by date for the same reason: a
    queued/delayed publish is still the right post)."""
    dias = abs((fecha_post - fecha_solicitud).total_seconds()) / 86400
    if dias >= _VENTANA_FECHA_DIAS:
        return 0.0
    return 1 - (dias / _VENTANA_FECHA_DIAS)


def calcular_coincidencia(
    *,
    solicitud_titulo: str | None,
    solicitud_texto: str,
    solicitud_cliente_nombre: str | None,
    solicitud_fecha_recepcion: datetime,
    post_texto: str,
    post_fecha_publicacion: datetime,
) -> float:
    """Return a 0.0–1.0 match confidence between a solicitud and a Meta post.

    Combines three explainable signals — word overlap between the
    solicitud's título/texto and the post's caption, whether the client's
    name shows up in that caption, and how close the post's date is to
    the solicitud's `fecha_recepcion` — weighted `_PESO_TEXTO`/
    `_PESO_CLIENTE`/`_PESO_FECHA`. No single maxed-out signal alone
    reaches 1.0.
    """
    solicitud_tokens = _tokenizar(f"{solicitud_titulo or ''} {solicitud_texto}")
    post_tokens = _tokenizar(post_texto)
    return round(
        _PESO_TEXTO * _score_texto(solicitud_tokens, post_tokens)
        + _PESO_CLIENTE * _score_cliente(solicitud_cliente_nombre, post_tokens)
        + _PESO_FECHA * _score_fecha(solicitud_fecha_recepcion, post_fecha_publicacion),
        4,
    )
