"""Domain service: scan every due Radar source and persist what is new.

Sprint Fuentes (2026-10-29). Built to be cheap to run every hour on a small
Railway box — each choice below is about not wasting CPU, memory, bandwidth
or database round trips:

- **Only due sources are scanned.** Each source has its own
  `intervalo_minutos`; a cron that fires often still only touches the
  sources that are due. A source that keeps failing backs off (its wait is
  multiplied by `1 + errores_consecutivos`, capped at 24x) instead of being
  hammered. "Escanear ahora" passes `forzar=True` and skips this.
- **Conditional requests.** `etag`/`last_modified` from the previous scan
  are sent back; an unchanged feed answers `304` with no body to download
  or parse (`ResultadoFetch.not_modified`).
- **Network in parallel, database in sequence.** Fetching is I/O bound, so
  it runs on a small thread pool; the SQLAlchemy session is not
  thread-safe, so every database write happens afterwards, one source at
  a time, in the calling thread.
- **Bounded work per source.** Candidates older than `max_age_days` are
  dropped and at most `max_items` are kept (newest first), so a first scan
  of a site with years of archive never floods the Radar or the database.
- **One query to deduplicate** (`existing_hashes`) per source instead of
  one `exists` call per entry.
- **Metadata only.** A scan never resolves Google links or extracts
  articles — that stays on demand ("Preparar noticia").

Depends only on ports; no network or SQLAlchemy import here.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.ports.content_source import ContentSource, ContentSourceError, ResultadoFetch
from core.ports.unit_of_work import UnitOfWork
from shared.logger import get_logger

logger = get_logger(__name__)

ESTADO_OK = "ok"
ESTADO_SIN_CAMBIOS = "sin_cambios"
ESTADO_ERROR = "error"
ESTADO_OMITIDA = "omitida"

_FACTOR_BACKOFF_MAXIMO = 24
_ERROR_MAX_CHARS = 500


@dataclass(frozen=True, slots=True)
class ResultadoEscaneo:
    """What scanning one source did, for the UI/cron log to report."""

    fuente_id: str
    fuente: str
    estado: str
    consultados: int = 0
    nuevos: int = 0
    duplicados: int = 0
    error: str | None = None


def esta_pendiente(fuente: Source, ahora: datetime) -> bool:
    """Return whether `fuente` is enabled and due for a scan at `ahora`."""
    if not fuente.enabled:
        return False
    if fuente.last_scan is None:
        return True
    factor = min(1 + fuente.errores_consecutivos, _FACTOR_BACKOFF_MAXIMO)
    return ahora - fuente.last_scan >= timedelta(minutes=fuente.intervalo_minutos * factor)


def _traer(
    fuente: Source, fabrica: Callable[[Source], ContentSource]
) -> tuple[Source, ResultadoFetch | None, str | None]:
    """Fetch one source (runs on a worker thread — no database access here)."""
    try:
        adaptador = fabrica(fuente)
        condicional = getattr(adaptador, "fetch_condicional", None)
        if condicional is not None:
            return fuente, condicional(fuente.etag, fuente.last_modified), None
        return fuente, ResultadoFetch(candidates=adaptador.fetch_candidates()), None
    except ContentSourceError as exc:
        return fuente, None, str(exc)
    except Exception as exc:  # one broken adapter must never abort the whole scan
        logger.exception("Fallo inesperado al escanear '%s'", fuente.name)
        return fuente, None, f"Error inesperado: {exc}"


def _acotar(
    candidatos: list[NewsCandidate], fuente: Source, ahora: datetime
) -> list[NewsCandidate]:
    """Keep recent candidates only, newest first, at most `fuente.max_items`."""
    limite = ahora - timedelta(days=fuente.max_age_days)
    vigentes = [c for c in candidatos if c.published_at is None or c.published_at >= limite]
    vigentes.sort(key=lambda c: c.published_at or ahora, reverse=True)
    return vigentes[: fuente.max_items]


def escanear_fuentes(
    uow: UnitOfWork,
    fabrica: Callable[[Source], ContentSource],
    *,
    forzar: bool = False,
    ahora: datetime | None = None,
    max_workers: int = 4,
) -> list[ResultadoEscaneo]:
    """Scan the due sources (all enabled ones with `forzar`) and persist new candidates.

    Commits once per source, so a failure on one never loses the others.
    """
    ahora = ahora if ahora is not None else datetime.now(UTC)
    activas = [f for f in uow.sources.list_all() if f.enabled]
    objetivo = activas if forzar else [f for f in activas if esta_pendiente(f, ahora)]
    resultados = [
        ResultadoEscaneo(fuente_id=f.id, fuente=f.name, estado=ESTADO_OMITIDA)
        for f in activas
        if f not in objetivo
    ]
    if not objetivo:
        return resultados

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(objetivo)))) as pool:
        traidas = list(pool.map(lambda f: _traer(f, fabrica), objetivo))

    for fuente, resultado, error in traidas:
        try:
            resultados.append(_registrar(uow, fuente, resultado, error, ahora))
        except Exception as exc:  # e.g. a concurrent scan won the unique-hash race
            uow.rollback()
            logger.exception("No se pudo registrar el escaneo de '%s'", fuente.name)
            resultados.append(
                ResultadoEscaneo(
                    fuente_id=fuente.id,
                    fuente=fuente.name,
                    estado=ESTADO_ERROR,
                    error=f"No se pudo guardar: {exc}"[:_ERROR_MAX_CHARS],
                )
            )
    return resultados


def _registrar(
    uow: UnitOfWork,
    fuente: Source,
    resultado: ResultadoFetch | None,
    error: str | None,
    ahora: datetime,
) -> ResultadoEscaneo:
    if resultado is None:
        mensaje = (error or "Error desconocido")[:_ERROR_MAX_CHARS]
        uow.sources.save(
            replace(
                fuente,
                last_scan=ahora,
                last_error=mensaje,
                errores_consecutivos=fuente.errores_consecutivos + 1,
                last_new_count=0,
            )
        )
        uow.commit()
        return ResultadoEscaneo(
            fuente_id=fuente.id, fuente=fuente.name, estado=ESTADO_ERROR, error=mensaje
        )

    if resultado.not_modified:
        uow.sources.save(
            replace(
                fuente, last_scan=ahora, last_error=None, errores_consecutivos=0, last_new_count=0
            )
        )
        uow.commit()
        return ResultadoEscaneo(fuente_id=fuente.id, fuente=fuente.name, estado=ESTADO_SIN_CAMBIOS)

    vigentes = _acotar(resultado.candidates, fuente, ahora)
    existentes = uow.news_candidates.existing_hashes([c.hash for c in vigentes])
    nuevos: list[NewsCandidate] = []
    vistos = set(existentes)
    for candidato in vigentes:
        if candidato.hash not in vistos:
            vistos.add(candidato.hash)
            nuevos.append(candidato)
    for candidato in nuevos:
        uow.news_candidates.save(candidato)

    uow.sources.save(
        replace(
            fuente,
            last_scan=ahora,
            last_error=None,
            errores_consecutivos=0,
            etag=resultado.etag,
            last_modified=resultado.last_modified,
            last_new_count=len(nuevos),
        )
    )
    uow.commit()
    logger.info(
        "Escaneo de '%s': %d consultado(s), %d nuevo(s), %d duplicado(s)",
        fuente.name,
        len(resultado.candidates),
        len(nuevos),
        len(vigentes) - len(nuevos),
    )
    return ResultadoEscaneo(
        fuente_id=fuente.id,
        fuente=fuente.name,
        estado=ESTADO_OK,
        consultados=len(resultado.candidates),
        nuevos=len(nuevos),
        duplicados=len(vigentes) - len(nuevos),
    )
