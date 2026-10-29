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

## Discovery 4 (2026-10-29) — resolver que sí funciona contra Google Noticias

`agents/radar/google_news_source_resolver.py` (`GoogleNewsSourceResolver`)
reemplaza al resolver por redirect como el que usa `get_source_resolver`
(el redirect HTTP queda como `fallback` para URLs que no son de Google).
Lee la firma/timestamp del artículo en la página de Google Noticias y
pide la URL real al endpoint interno `batchexecute` (RPC `Fbv4je`).
Verificado contra el feed en vivo: **20/20 resueltas**, y el
`HtmlContentExtractor` extrajo título/cuerpo/imagen de El Pilón, Infobae
y Caracol. Ojo con la calidad de extracción por medio (p. ej. El Heraldo
trae menús/pie de página en el cuerpo).

**Frágil por naturaleza**: es un endpoint interno no documentado. Si
deja de funcionar, los candidatos vuelven a quedar en "Fuente pendiente de
resolver" (no rompe el flujo) — revisar primero el log
`google_news_source_resolver` ("Google Noticias cambió su formato?").

## Discovery 5 (2026-10-29) — "Crear noticia" redacta con IA y crea el borrador

`POST /discovery/{id}/crear-noticia` ahora (`core/services/candidate_draft_service.py`)
reescribe el `extracted_content` con la IA editorial (mismo prompt/Yoast que
las solicitudes, más reglas para notas de otros medios: redacción propia,
sin copiar), agrega "Fuente: medio" con enlace al final y crea un
**borrador** en WordPress (nunca publica). Guarda `wp_post_id`/`wp_url` en
el candidato y lo marca `PROCESADO`. Requiere "Preparar noticia" antes (422).
A diferencia de las solicitudes de WhatsApp, si la IA falla **no** se crea
el borrador (502): el texto crudo es de otro medio y no debe republicarse
tal cual. Sin imagen destacada (la imagen de la nota pertenece al medio
original; la portada propia es el siguiente paso).

## Sprint Fuentes (2026-10-29) — fuentes paramétricas y escaneo

Las fuentes ya no se arman a mano en un script: viven en la tabla `sources`
(`core.entities.source.Source`) y se gestionan desde **Radar → Fuentes**
(agregar con vista previa, pausar, frecuencia). `GET/POST/PATCH
/radar-fuentes`, `POST /radar-fuentes/probar` y `POST /radar-fuentes/escanear`
("Escanear ahora"). Hoy hay un tipo, `rss`; `agents/radar/fabrica.py` es el
único lugar donde se agrega otro (p. ej. Instagram). La fuente de Google
Noticias se migró con su id de siempre (`radar-google-news-vallenato`) para
no romper la deduplicación por huella.

**"Actualizar Radar" no escanea**: solo vuelve a leer lo guardado. Trae noticias
nuevas "Escanear ahora" o el cron.

### Escaneo automático (Railway)

`python -m scripts.escanear_fuentes` solo consulta las fuentes a las que ya les
toca (cada una tiene su `intervalo_minutos`), así que se puede disparar cada
hora. Crear en Railway un servicio **Cron** del mismo repo/imagen, con
`DATABASE_URL` referenciada igual que la app, *Start Command* =
`python -m scripts.escanear_fuentes` y *Cron Schedule* = `0 * * * *`. El
contenedor arranca, escanea y termina: no mantiene un proceso encendido.

### Qué se hizo para gastar poco

- Solo se escanean las fuentes vencidas; una que falla espera `intervalo × (1 +
  fallos seguidos)` (tope 24x) en vez de insistir.
- Peticiones condicionales (`ETag`/`Last-Modified`): un feed sin cambios responde
  `304` sin cuerpo que descargar ni interpretar.
- Descarga en paralelo (4 hilos) y escritura a la base en serie; un solo
  `SELECT ... IN` por fuente para deduplicar (antes uno por entrada).
- Tope por fuente: `max_items` (20) y `max_age_days` (7), para que la primera
  vez no entren años de archivo.
- El escaneo solo trae metadatos: resolver y extraer sigue siendo bajo demanda.
- `GET /discovery` solo carga los *nuevos* de los últimos 30 días (más todo lo ya
  revisado); `?dias=0` trae todo. Índices en `discovered_at` y `estado`.
- Un solo escaneo a la vez por proceso (409 si ya hay uno).

**Seguridad**: las URL que escribe el operador las consulta el servidor, así que
se rechazan direcciones internas (`agents/radar/url_segura.py`). Limitación:
una web pública que redirija a una dirección interna no se detecta.

## Lo que falta (Discovery 6+)
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
