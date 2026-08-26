# Radar Agent

**Estado:** Parcialmente implementado (Sprint Discovery 1, 2026-08-25 —
Sprint Discovery 2, 2026-08-26).

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

## Lo que falta (Discovery 3+)

- Más de una fuente simultánea (`descubrir` ya acepta un `ContentSource`
  por llamada; falta orquestar varias y agregar sus resultados).
- Resolver el redirect de Google Noticias (`news.google.com/rss/articles/...`)
  a la URL real del medio — hoy es suficiente para identificar la
  noticia, pero un futuro Extractor necesita la URL real para sacar el
  cuerpo del artículo. El botón "Ver fuente" del Radar Editorial abre
  ese link tal cual, con un aviso visible de la limitación.
- `Source` persistido y gestionable (hoy se construye a mano en el
  script, no vive en base de datos).
- Lo que pasa después de "Crear noticia": ni `Article` ni
  `EditorialTask` tienen hoy un campo que los enlace a un
  `NewsCandidate`, y no existe `ArticleRepository`/`EditorialTaskRepository`
  en `core/ports/` ni en `UnitOfWork` — construir esa persistencia real
  es trabajo de Discovery 3, deliberadamente no resuelto aquí.
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
