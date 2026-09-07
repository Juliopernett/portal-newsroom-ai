# Radar Agent

**Estado:** Parcialmente implementado (Sprint Discovery 1, 2026-08-25 —
Sprint Discovery 3, 2026-08-29).

## Lo que ya existe

- `rss_content_source.py`: `RssContentSource`, el primer `ContentSource`
  real — lee un feed RSS/Atom real por HTTP (`requests` + `feedparser`) y
  lo normaliza a `NewsCandidate`. Hoy apunta al RSS de Google Noticias
  para "vallenato" (`Settings.radar_rss_feed_url`, overrideable por
  `.env`). `summary` se limpia de marcado HTML (`_clean_summary`,
  Discovery 2) — Google Noticias mete un snippet `<a>`/`<font>` en
  `<description>` que se veía crudo en el Radar Editorial.
- `core.services.radar_service.descubrir(source, repository)`: corre
  `DiscoveryEngine.run([source])` (sin cambios) y persiste solo los
  candidatos que `NewsCandidateRepository.exists(hash)` no conocía
  todavía — la deduplicación *entre* pasadas que el `DiscoveryEngine` en
  sí deliberadamente no hace. Devuelve un `ResultadoDescubrimiento`
  (consultados/nuevos/duplicados/errores).
- Persistencia real: `database/models/news_candidate.py` +
  `database/repositories/news_candidate_repository.py` (tabla
  `news_candidates`, `hash` único, `estado`).
- Ejecutable a mano: `python -m scripts.descubrir_noticias`.
- **Radar Editorial** (Discovery 2): pantalla en Newsroom
  (`frontend/src/features/radar/`, ruta `/radar`) donde un humano revisa
  cada `NewsCandidate` y decide `Guardar`/`Descartar`/`Crear noticia` —
  ver `core/services/news_candidate_service.py` (transiciones de
  `EstadoNewsCandidate`: `NUEVO → GUARDADO|DESCARTADO|PROCESADO`,
  `PROCESADO` es terminal) y `app/api/routers/discovery.py`
  (`GET /discovery`, `POST /discovery/{id}/guardar|descartar|crear-noticia`).
  "Crear noticia" **solo** marca `PROCESADO` — no genera contenido ni
  crea `Article`/`PublicationRequest` (ver "Lo que falta" abajo).

## Discovery 3 (2026-08-29) — resolver la fuente + preparar el Extractor

`NewsCandidate.url` (el enlace de Google Noticias) ahora se puede
resolver a la URL real del medio (`url_fuente_original`,
`estado_resolucion`) y esa página extraerse a `extracted_content` — ver
`core/services/source_resolution_service.py`, el puerto nuevo
`core.ports.source_resolver.SourceResolver` y la primera implementación
real de `core.ports.content_extractor.ContentExtractor`
(`agents/extractor/html_content_extractor.py`). Acción nueva en el Radar
Editorial: **"Preparar noticia"** (`POST /discovery/{id}/preparar`),
independiente de `Guardar`/`Descartar`/`Crear noticia`.

**Hallazgo real, verificado contra el feed en vivo (20 URLs, sin
mocks)**: **el resolver por redirect HTTP falla en el 100% de los
casos actuales** — Google Noticias emite un 302 real, pero apunta a
*otra* URL dentro de `news.google.com` (el shell de su app cliente),
que requiere JavaScript para llegar al medio real. Confirmado que no
depende del `User-Agent` (probado también como Googlebot). Esto no es
un bug de `HttpRedirectSourceResolver` — es exactamente el escenario
que su propio diseño anticipa y reporta como `ResolvedSource(success=False)`
en vez de romper el pipeline. El botón "Preparar noticia" del Radar
Editorial hoy, con este adaptador, casi siempre terminará en "Fuente
pendiente de resolver" — esperado, no un error a corregir en este
sprint.

## Lo que falta (Discovery 4+)

- **Un `SourceResolver` que sí funcione contra Google Noticias** — el
  puerto ya existe exactamente para esto (ver el hallazgo arriba).
  Candidatos: ejecutar la redirección con un navegador real
  (Playwright, ya está en `requirements.txt` sin usar) o decodificar el
  esquema de URL que Google usa para codificar el destino real
  (enfoque usado por proyectos open-source de scraping de Google News —
  no evaluado en este sprint, y frágil por naturaleza: se rompe si
  Google cambia el formato).
- Extracción con JavaScript para medios cuya página también lo
  requiere (mismo motivo — `HtmlContentExtractor` es deliberadamente
  solo HTTP + BeautifulSoup, ver `agents/extractor/README.md`).
- Más de una fuente simultánea (`descubrir` ya acepta un `ContentSource`
  por llamada; falta orquestar varias y agregar sus resultados).
- `Source` persistido y gestionable (hoy se construye a mano en el
  script, no vive en base de datos).
- El Writer real (reescritura con IA) y `Article`/`EditorialTask`
  persistidos de verdad, enlazados a un `NewsCandidate` — ninguno de
  los dos tiene hoy ese campo, ni existe `ArticleRepository`/
  `EditorialTaskRepository` en `core/ports/`/`UnitOfWork`.
- El mapeo a `PublicationRequest` vía `RadarPublicationInboxAdapter` (ver
  [ADR-003](../../docs/adr/ADR-003-publication-inbox.md)) — ese ADR
  asume campos (`origin`/`is_commercial`) que `PublicationRequest` no
  tiene hoy (es exclusivamente comercial); no seguir ese diseño tal cual
  sin revisarlo primero.
- Un scheduler (hoy es un script disparado a mano, igual que
  `scripts/purgar_media_expirados.py` — deliberado, no un descuido).

## Depende de

- `core.services.discovery_engine.DiscoveryEngine`
- `core.ports.content_source.ContentSource` (uno o más adaptadores reales)
- `core.ports.repository.Repository` (para descartar duplicados contra el
  historial editorial)

## Produce

Un evento `NewsFound` con los candidatos nuevos. Desde Sprint 3A, esto no
va directo al Extractor: un `RadarPublicationInboxAdapter` (ver
[docs/architecture/publication-inbox.md](../../docs/architecture/publication-inbox.md))
mapea cada `NewsCandidate` a un `PublicationRequest` (`origin=RADAR`,
`is_commercial=False`), que converge con los demás canales de entrada
(WhatsApp, entrada manual) antes de llegar al Extractor. `DiscoveryEngine`
en sí no cambia — Radar sigue siendo uno de varios canales de **Publication
Inbox**, no el único punto de entrada del sistema. Ver
[ADR-003](../../docs/adr/ADR-003-publication-inbox.md).
