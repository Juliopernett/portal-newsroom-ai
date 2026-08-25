# Radar Agent

**Estado:** Parcialmente implementado (Sprint Discovery 1, 2026-08-25).

## Lo que ya existe

- `rss_content_source.py`: `RssContentSource`, el primer `ContentSource`
  real — lee un feed RSS/Atom real por HTTP (`requests` + `feedparser`) y
  lo normaliza a `NewsCandidate`. Hoy apunta al RSS de Google Noticias
  para "vallenato" (`Settings.radar_rss_feed_url`, overrideable por
  `.env`).
- `core.services.radar_service.descubrir(source, repository)`: corre
  `DiscoveryEngine.run([source])` (sin cambios) y persiste solo los
  candidatos que `NewsCandidateRepository.exists(hash)` no conocía
  todavía — la deduplicación *entre* pasadas que el `DiscoveryEngine` en
  sí deliberadamente no hace. Devuelve un `ResultadoDescubrimiento`
  (consultados/nuevos/duplicados/errores).
- Persistencia real: `database/models/news_candidate.py` +
  `database/repositories/news_candidate_repository.py` (tabla
  `news_candidates`, `hash` único).
- Ejecutable a mano: `python -m scripts.descubrir_noticias`.

## Lo que falta (Discovery 2+)

- Más de una fuente simultánea (`descubrir` ya acepta un `ContentSource`
  por llamada; falta orquestar varias y agregar sus resultados).
- Resolver el redirect de Google Noticias (`news.google.com/rss/articles/...`)
  a la URL real del medio — hoy es suficiente para identificar la
  noticia, pero un futuro Extractor necesita la URL real para sacar el
  cuerpo del artículo.
- `Source` persistido y gestionable (hoy se construye a mano en el
  script, no vive en base de datos).
- El mapeo a `PublicationRequest` vía `RadarPublicationInboxAdapter` (ver
  [ADR-003](../../docs/adr/ADR-003-publication-inbox.md)) — Radar
  todavía no converge con los demás canales de Publication Inbox.
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
