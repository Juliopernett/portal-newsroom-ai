"""Unit tests for source_scan_service — in-memory repositories, fake adapters, no network."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.ports.content_source import ContentSourceError, ResultadoFetch
from core.services.source_scan_service import (
    ESTADO_ERROR,
    ESTADO_OK,
    ESTADO_OMITIDA,
    ESTADO_SIN_CAMBIOS,
    escanear_fuentes,
    esta_pendiente,
)

AHORA = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


class _Fuentes:
    def __init__(self, fuentes: list[Source]) -> None:
        self.por_id = {f.id: f for f in fuentes}

    def save(self, entity: Source) -> None:
        self.por_id[entity.id] = entity

    def get_by_id(self, id: str) -> Source | None:
        return self.por_id.get(id)

    def list_all(self) -> list[Source]:
        return list(self.por_id.values())


class _Candidatos:
    def __init__(self, existentes: Sequence[str] = ()) -> None:
        self.hashes = set(existentes)
        self.guardados: list[NewsCandidate] = []
        self.consultas_existentes = 0

    def existing_hashes(self, hashes: Sequence[str]) -> set[str]:
        self.consultas_existentes += 1
        return {h for h in hashes if h in self.hashes}

    def save(self, entity: NewsCandidate) -> None:
        self.hashes.add(entity.hash)
        self.guardados.append(entity)


class _UoW:
    def __init__(self, fuentes: list[Source], existentes: Sequence[str] = ()) -> None:
        self.sources = _Fuentes(fuentes)
        self.news_candidates = _Candidatos(existentes)
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _Adaptador:
    def __init__(self, resultado: ResultadoFetch | Exception) -> None:
        self.resultado = resultado
        self.recibio: tuple[str | None, str | None] | None = None

    def fetch_condicional(self, etag: str | None, last_modified: str | None) -> ResultadoFetch:
        self.recibio = (etag, last_modified)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def _fuente(id: str = "f1", **kwargs: object) -> Source:
    base: dict[str, object] = {
        "id": id,
        "name": f"Fuente {id}",
        "type": "rss",
        "url": f"https://{id}.com/feed",
    }
    base.update(kwargs)
    return Source(**base)


def _cand(fuente_id: str, n: int, dias_atras: float = 0.5) -> NewsCandidate:
    return NewsCandidate(
        source=fuente_id,
        title=f"Titular {n}",
        url=f"https://{fuente_id}.com/{n}",
        summary="",
        hash=f"{fuente_id}-{n}",
        published_at=AHORA - timedelta(days=dias_atras),
    )


def _fabrica(adaptadores: dict[str, _Adaptador]):
    return lambda fuente: adaptadores[fuente.id]


# --- esta_pendiente --------------------------------------------------------


def test_a_source_never_scanned_is_due() -> None:
    assert esta_pendiente(_fuente(), AHORA) is True


def test_a_disabled_source_is_never_due() -> None:
    assert esta_pendiente(_fuente(enabled=False), AHORA) is False


def test_a_source_is_due_only_once_its_interval_has_passed() -> None:
    reciente = _fuente(last_scan=AHORA - timedelta(minutes=30), intervalo_minutos=60)
    vencida = _fuente(last_scan=AHORA - timedelta(minutes=61), intervalo_minutos=60)

    assert esta_pendiente(reciente, AHORA) is False
    assert esta_pendiente(vencida, AHORA) is True


def test_a_failing_source_backs_off() -> None:
    # 2 consecutive errors → waits 3x the interval.
    fuente = _fuente(
        last_scan=AHORA - timedelta(minutes=150), intervalo_minutos=60, errores_consecutivos=2
    )

    assert esta_pendiente(fuente, AHORA) is False
    assert (
        esta_pendiente(
            _fuente(
                last_scan=AHORA - timedelta(minutes=181),
                intervalo_minutos=60,
                errores_consecutivos=2,
            ),
            AHORA,
        )
        is True
    )


# --- escanear_fuentes ------------------------------------------------------


def test_scans_due_sources_and_skips_the_rest() -> None:
    due = _fuente("due")
    reciente = _fuente("reciente", last_scan=AHORA - timedelta(minutes=5))
    uow = _UoW([due, reciente])
    adaptadores = {"due": _Adaptador(ResultadoFetch(candidates=[_cand("due", 1)]))}

    resultados = escanear_fuentes(uow, _fabrica(adaptadores), ahora=AHORA)

    estados = {r.fuente_id: r.estado for r in resultados}
    assert estados == {"due": ESTADO_OK, "reciente": ESTADO_OMITIDA}


def test_forzar_scans_every_enabled_source_regardless_of_interval() -> None:
    reciente = _fuente("reciente", last_scan=AHORA - timedelta(minutes=5))
    apagada = _fuente("apagada", enabled=False)
    uow = _UoW([reciente, apagada])
    adaptadores = {"reciente": _Adaptador(ResultadoFetch(candidates=[_cand("reciente", 1)]))}

    resultados = escanear_fuentes(uow, _fabrica(adaptadores), forzar=True, ahora=AHORA)

    assert [r.fuente_id for r in resultados] == ["reciente"]
    assert resultados[0].estado == ESTADO_OK


def test_saves_only_new_candidates_and_deduplicates_with_one_query() -> None:
    uow = _UoW([_fuente()], existentes=["f1-1"])
    adaptador = _Adaptador(
        ResultadoFetch(candidates=[_cand("f1", 1), _cand("f1", 2), _cand("f1", 3)])
    )

    (resultado,) = escanear_fuentes(uow, _fabrica({"f1": adaptador}), ahora=AHORA)

    assert (resultado.consultados, resultado.nuevos, resultado.duplicados) == (3, 2, 1)
    assert [c.hash for c in uow.news_candidates.guardados] == ["f1-2", "f1-3"]
    assert uow.news_candidates.consultas_existentes == 1


def test_drops_old_candidates_and_caps_the_count_newest_first() -> None:
    fuente = _fuente(max_items=2, max_age_days=7)
    candidatos = [
        _cand("f1", 1, dias_atras=1),
        _cand("f1", 2, dias_atras=0.1),
        _cand("f1", 3, dias_atras=2),
        _cand("f1", 4, dias_atras=30),  # too old
    ]
    uow = _UoW([fuente])

    escanear_fuentes(
        uow, _fabrica({"f1": _Adaptador(ResultadoFetch(candidates=candidatos))}), ahora=AHORA
    )

    assert [c.hash for c in uow.news_candidates.guardados] == ["f1-2", "f1-1"]


def test_sends_the_previous_validators_and_stores_the_new_ones() -> None:
    fuente = _fuente(etag="viejo", last_modified="ayer")
    uow = _UoW([fuente])
    adaptador = _Adaptador(
        ResultadoFetch(candidates=[_cand("f1", 1)], etag="nuevo", last_modified="hoy")
    )

    escanear_fuentes(uow, _fabrica({"f1": adaptador}), ahora=AHORA)

    assert adaptador.recibio == ("viejo", "ayer")
    guardada = uow.sources.get_by_id("f1")
    assert guardada is not None
    assert (guardada.etag, guardada.last_modified) == ("nuevo", "hoy")
    assert guardada.last_scan == AHORA
    assert guardada.last_new_count == 1


def test_not_modified_saves_nothing_and_keeps_the_validators() -> None:
    uow = _UoW([_fuente(etag="e1")])
    adaptador = _Adaptador(ResultadoFetch(etag="e1", not_modified=True))

    (resultado,) = escanear_fuentes(uow, _fabrica({"f1": adaptador}), ahora=AHORA)

    assert resultado.estado == ESTADO_SIN_CAMBIOS
    assert uow.news_candidates.guardados == []
    assert uow.news_candidates.consultas_existentes == 0
    assert uow.sources.get_by_id("f1").etag == "e1"  # type: ignore[union-attr]


def test_a_failing_source_is_recorded_and_does_not_stop_the_others() -> None:
    uow = _UoW([_fuente("mala"), _fuente("buena")])
    adaptadores = {
        "mala": _Adaptador(ContentSourceError("sitio caído")),
        "buena": _Adaptador(ResultadoFetch(candidates=[_cand("buena", 1)])),
    }

    resultados = escanear_fuentes(uow, _fabrica(adaptadores), ahora=AHORA)

    por_id = {r.fuente_id: r for r in resultados}
    assert por_id["mala"].estado == ESTADO_ERROR
    assert por_id["mala"].error == "sitio caído"
    assert por_id["buena"].estado == ESTADO_OK
    mala = uow.sources.get_by_id("mala")
    assert mala is not None
    assert (mala.errores_consecutivos, mala.last_error) == (1, "sitio caído")


def test_an_unexpected_adapter_exception_is_contained() -> None:
    uow = _UoW([_fuente()])

    (resultado,) = escanear_fuentes(
        uow, _fabrica({"f1": _Adaptador(RuntimeError("boom"))}), ahora=AHORA
    )

    assert resultado.estado == ESTADO_ERROR
    assert "boom" in (resultado.error or "")


def test_a_successful_scan_clears_the_error_state() -> None:
    uow = _UoW([_fuente(errores_consecutivos=3, last_error="antes falló")])
    adaptador = _Adaptador(ResultadoFetch(candidates=[_cand("f1", 1)]))

    escanear_fuentes(uow, _fabrica({"f1": adaptador}), forzar=True, ahora=AHORA)

    fuente = uow.sources.get_by_id("f1")
    assert fuente is not None
    assert (fuente.errores_consecutivos, fuente.last_error) == (0, None)


def test_a_save_failure_rolls_back_and_is_reported() -> None:
    uow = _UoW([_fuente()])

    def _romper(entity: NewsCandidate) -> None:
        raise RuntimeError("violación de unicidad")

    uow.news_candidates.save = _romper  # type: ignore[method-assign]

    (resultado,) = escanear_fuentes(
        uow, _fabrica({"f1": _Adaptador(ResultadoFetch(candidates=[_cand("f1", 1)]))}), ahora=AHORA
    )

    assert resultado.estado == ESTADO_ERROR
    assert uow.rollbacks == 1
