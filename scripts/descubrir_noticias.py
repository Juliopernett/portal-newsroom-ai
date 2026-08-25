"""Run one real Discovery pass over the configured RSS source and report it.

Sprint Discovery 1 (2026-08-25). A deliberate ops-triggered script, not a
scheduler running inside the FastAPI process — same reasoning as
`scripts/purgar_media_expirados.py`: fewer moving parts in a system
already carrying real production traffic. Run it by hand, or schedule it
via Railway's cron support — the script itself doesn't change either way.

Idempotent: every `NewsCandidate` this script would persist twice for the
same underlying news item is instead counted as `Duplicados` and skipped
(see `core.services.radar_service.descubrir`) — running this twice in a
row against an unchanged feed reports `Nuevos: 0` the second time.

Usage:
    python -m scripts.descubrir_noticias
"""

from __future__ import annotations

from agents.radar.rss_content_source import RssContentSource
from config.settings import get_settings
from core.entities.source import Source
from core.services.radar_service import ResultadoDescubrimiento, descubrir
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork


def _imprimir_resultado(resultado: ResultadoDescubrimiento) -> None:
    print(f"Fuente: {resultado.fuente}")
    print(f"Consultados: {resultado.consultados}")
    print(f"Nuevos: {resultado.nuevos}")
    print(f"Duplicados: {resultado.duplicados}")
    print(f"Errores: {resultado.errores}")


def main() -> None:
    settings = get_settings()
    source = Source(
        # `id` no puede ser el aleatorio por defecto: el hash de
        # deduplicación (`core.services.deduplication.generate_candidate_hash`)
        # se calcula sobre `(source.id, url)`, así que un id distinto en
        # cada corrida rompería la idempotencia entre ejecuciones — la
        # misma noticia parecería "nueva" cada vez. Fijo mientras `Source`
        # no esté persistido (ver agents/radar/README.md).
        id="radar-google-news-vallenato",
        name="Google Noticias — vallenato",
        type="rss",
        url=settings.radar_rss_feed_url,
    )
    adapter = RssContentSource(source)

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        resultado = descubrir(adapter, uow.news_candidates)
        uow.commit()

    _imprimir_resultado(resultado)


if __name__ == "__main__":
    main()
