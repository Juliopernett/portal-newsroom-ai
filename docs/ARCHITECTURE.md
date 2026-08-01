# Arquitectura

## Estilo arquitectónico

Portal Newsroom AI usa **arquitectura hexagonal (Ports & Adapters)**, con la
regla de dependencia de **Clean Architecture**: las dependencias siempre
apuntan hacia adentro, nunca hacia afuera.

```
        ┌─────────────────────────────────────────────┐
        │                    app/                      │  entrypoint / composition root
        │       ┌─────────────────────────────────┐    │
        │       │           workflows/             │    │  pipelines (orquestación determinística)
        │       │   ┌───────────────────────────┐   │    │
        │       │   │          agents/           │   │    │  casos de uso (Radar, Writer, ...)
        │       │   │   ┌───────────────────┐   │   │    │
        │       │   │   │       core/        │   │   │    │  dominio: entidades, ports, excepciones
        │       │   │   │  (sin dependencias │   │   │    │
        │       │   │   │   externas)        │   │   │    │
        │       │   │   └───────────────────┘   │   │    │
        │       │   └───────────────────────────┘   │    │
        │       └─────────────────────────────────┘    │
        └─────────────────────────────────────────────┘
                    ▲                    ▲
                    │                    │
             database/            (futuras integraciones:
        (adaptador de           WordPress, Telegram, IA)
         persistencia)
```

`core/` no importa SQLAlchemy, Playwright, `requests`, ni ningún SDK
externo. Solo define **qué** necesita el dominio (contratos), nunca
**cómo** se resuelve. `database/`, y las futuras integraciones con
WordPress/Telegram/proveedores de IA, son **adaptadores** que implementan
esos contratos.

## Por qué esta arquitectura

- **Reemplazabilidad real.** El requisito de negocio "si cambiamos WordPress
  por otro CMS, solo cambia el módulo WordPress" se resuelve directamente
  con Ports & Adapters: `agents/wordpress/` depende de
  `core.ports.cms_publisher.CMSPublisher`, no de la librería HTTP concreta.
  Un nuevo CMS solo requiere un nuevo adaptador que implemente ese mismo
  contrato.
- **Testabilidad.** Como los agentes dependen de contratos (`Protocol`), en
  las pruebas se pueden usar implementaciones falsas sin tocar WordPress,
  Telegram ni ningún servicio de IA real.
- **Simplicidad sobre sobre-ingeniería.** No se introduce una capa de API
  (FastAPI), ni microservicios, ni un bus de eventos: no hay ningún
  requisito actual que lo justifique. Se agregará si una fase futura lo
  necesita.

## Ejemplo concreto: reemplazar WordPress

1. Hoy: `agents/wordpress/` implementará `core.ports.cms_publisher.CMSPublisher`
   usando la REST API de WordPress.
2. Mañana, si se migra a otro CMS: se crea `agents/<nuevo_cms>/` que
   implementa el mismo `CMSPublisher`. Ningún otro agente, workflow, ni
   `core/`, se modifica.

## Capas y carpetas

### `app/` — Composition root

Punto de entrada del proceso. Inicializa configuración y logging, y (a
partir de fases futuras) conecta agentes y workflows concretos con sus
adaptadores. Es la única capa que puede conocer "todo el grafo" de
dependencias.

### `core/` — Dominio

- `core/entities/`: modelos de dominio. Desde Sprint 2: `NewsCandidate`,
  `Source`, `Article`, `EditorialTask` — dataclasses inmutables
  (`frozen=True, slots=True, kw_only=True`), sin Pydantic ni ninguna otra
  dependencia externa, consistente con que `core/` no tiene dependencias
  de infraestructura.
- `core/ports/`: contratos (`typing.Protocol`) que describen lo que cada
  agente necesita de una fuente de contenido, un extractor, un proveedor de
  IA, un proveedor de imágenes, un publicador de CMS, un notificador y un
  repositorio de persistencia/historial. Desde Sprint 2, `ContentSource`
  devuelve `list[NewsCandidate]` (antes `list[str]`, antes de que la
  entidad existiera) y expone la `Source` que representa.
- `core/events/`: eventos de dominio — hechos de negocio ya ocurridos.
  Desde Sprint 2, `NewsFound` tiene payload real (`candidates`,
  `occurred_at`), emitido por `DiscoveryEngine`. `ArticleRewritten`,
  `DraftCreated` y `NotificationRequested` siguen siendo clases vacías,
  pendientes del sprint del agente que las necesite. Ver "Eventos de
  dominio" más abajo.
- `core/services/`: servicios de dominio — lógica de negocio pura que no
  pertenece a una única entidad (ver `core/services/README.md`). Desde
  Sprint 2: `generate_candidate_hash` (deduplicación) y `DiscoveryEngine`.
  Ver "Discovery Engine" más abajo.
- `core/exceptions.py`: jerarquía de errores de negocio
  (`DomainError` y subclases).

### `agents/` — Aplicación (casos de uso)

Un paquete por responsabilidad. Cada agente depende únicamente de los
`ports` de `core/` que necesita, nunca de un adaptador concreto:

| Agente | Responsabilidad | Port principal |
|---|---|---|
| `radar` | Detectar noticias nuevas (un canal de Publication Inbox) | `ContentSource`, `Repository`, `core.services.DiscoveryEngine` |
| `whatsapp` | Recibir solicitudes comerciales por WhatsApp (otro canal de Publication Inbox) | `PublicationInboxChannel` |
| `extractor` | Extraer contenido estructurado | `ContentExtractor` |
| `writer` | Reescribir con estilo editorial | `AIProvider` |
| `seo` | Generar metadatos SEO | `AIProvider` |
| `images` | Gestionar imágenes | `ImageProvider` |
| `wordpress` | Crear borradores en el CMS | `CMSPublisher` |
| `telegram` | Notificar al equipo editorial | `Notifier` |
| `scheduler` | Ejecutar pipelines periódicamente | — (usa `workflows/`) |
| `social` | Generar contenido para redes | `AIProvider` |
| `analytics` | Métricas editoriales | `Repository` |
| `orchestrator` | Coordinación inteligente multi-agente | todos los anteriores |

Hoy cada paquete es un placeholder documentado (`README.md`); la
implementación llega en fases futuras del roadmap.

**Commercial Manager no es un agente** — es un bounded context propio, con
sus propias entidades y reglas de negocio (ver "Publication Inbox y
Commercial Manager" más abajo), no una automatización de una tarea
mecánica del pipeline.

### `workflows/`

Composición determinística de agentes en pipelines de negocio (por ejemplo:
`Radar → Extractor → Writer → SEO → Images → WordPress(borrador) →
Telegram(notificación) → espera de aprobación humana`). Se diferencia de
`agents/orchestrator/` en que un workflow es una secuencia fija definida por
el equipo técnico, mientras que el orquestador puede tomar decisiones
dinámicas sobre qué agentes ejecutar.

### `database/` — Adaptador de persistencia

- `database/engine.py`: engine y session factory de SQLAlchemy, construidos
  a partir de `config/settings.py`. Cambiar de SQLite a PostgreSQL es
  cambiar `DATABASE_URL`, no código.
- `database/base.py`: `DeclarativeBase` compartida por los futuros modelos.
- `database/models/`: modelos ORM (a partir de la Fase 1).
- `database/repositories/`: implementaciones concretas de
  `core.ports.repository.Repository` (a partir de la Fase 1).
- `database/migrations/`: migraciones (Alembic, a configurar cuando exista
  el primer modelo real).

### `config/`

Única fuente de verdad de configuración. `config/settings.py` expone una
clase `Settings` (Pydantic) que lee `.env`. Ningún otro módulo debe leer
`os.environ` directamente — ver [PROJECT_RULES.md](PROJECT_RULES.md).

### `shared/`

Utilidades técnicas transversales que no pertenecen al dominio ni a ningún
agente en particular. Hoy: `shared/logger.py`, el logging centralizado.

### `prompts/`

Plantillas de prompts de IA como archivos de texto/markdown, separadas del
código Python para que el equipo editorial pueda revisarlas y ajustarlas
sin tocar la aplicación.

### `tests/`

Refleja la estructura del proyecto: `tests/unit/` para pruebas aisladas
(con dobles de prueba en lugar de adaptadores reales) y
`tests/integration/` para pruebas que ejercitan adaptadores reales
(base de datos de prueba, etc.).

### `docker/`

`Dockerfile` de la aplicación. `docker-compose.yml` (en la raíz) define
cómo se ejecuta en desarrollo/producción.

## Flujo de datos previsto (a partir de la Fase 4)

```
Fuente externa
     │
     ▼
 [Radar]  ──detecta──▶  [Repository] (¿ya existe? → descarta duplicado)
     │ nuevo
     ▼
 [Extractor] ──▶ contenido estructurado
     │
     ▼
 [Writer] ──▶ artículo reescrito
     │
     ▼
 [SEO] ──▶ metadatos SEO
     │
     ▼
 [Images] ──▶ imágenes gestionadas
     │
     ▼
 [WordPress] ──▶ BORRADOR (nunca publicación)
     │
     ▼
 [Telegram] ──▶ notificación al equipo editorial
     │
     ▼
 Aprobación humana ──▶ [Repository] registra la decisión (historial editorial)
```

## Discovery Engine (Sprint 2)

`core.services.discovery_engine.DiscoveryEngine` es el motor detrás del
futuro agente Radar — no es el agente en sí. Recibe una colección de
adaptadores `ContentSource`, y por cada uno **habilitado**:

1. Pide sus candidatos (`fetch_candidates() -> list[NewsCandidate]`).
2. Deduplica por `hash` (huella calculada por el adaptador vía
   `core.services.deduplication.generate_candidate_hash`), quedándose con
   la primera aparición.
3. Ordena el resultado por prioridad de la fuente, luego por `confidence`,
   luego por título.
4. Devuelve un evento `NewsFound` con el resultado.

No hace scraping, no llama IA, no persiste nada — cualquiera de esas cosas
es responsabilidad de un adaptador `ContentSource` concreto (que todavía
no existe) o de quien consuma el `NewsFound` que devuelve. Para probarlo
sin red existe `tests/fakes/FakeContentSource`, que lee JSON de
`tests/fixtures/` en lugar de una fuente real — nunca se importa desde
código de producción.

Lo que falta para que `agents/radar/` exista de verdad (fases futuras):
un `ContentSource` real por fuente (RSS, crawler, ...), un
`core.ports.repository.Repository` que descarte contra el historial
editorial persistido (hoy la deduplicación es solo dentro de una misma
pasada), y un `workflow` que llame a todo esto con una cadencia.

## Publication Inbox y Commercial Manager (Sprint 3A — diseño, no implementado)

Sprint 3A reposicionó el proyecto: para el cliente piloto, la mayoría de
las publicaciones no llegan por Discovery, llegan por WhatsApp desde
managers, artistas y empresas. Se diseñaron dos bounded contexts nuevos —
ver [ADR-003](adr/ADR-003-publication-inbox.md) y
[ADR-004](adr/ADR-004-commercial-manager.md):

- **Publication Inbox** (`docs/architecture/publication-inbox.md`):
  converge cualquier canal de entrada (WhatsApp, Radar, entrada manual,
  Email futuro) en una entidad única, `PublicationRequest`, antes de
  entrar al pipeline editorial existente (`Extractor` en adelante, sin
  cambios). Radar sigue usando `DiscoveryEngine` exactamente igual — un
  adaptador nuevo lo envuelve, no lo modifica.
- **Commercial Manager** (`docs/architecture/commercial-manager.md`):
  administra `Client`, `CommercialContact`, `Contract`, `Plan`,
  `Campaign`, `PublicationRegistryEntry` y `Alert` — la relación comercial
  detrás de ese contenido. Se conecta con Publication Inbox y con
  Editorial **solo por referencias de ID**, nunca importando entidades de
  un contexto en el otro; la coordinación cuando hace falta ocurre en
  `workflows/`, el mismo mecanismo que ya usa el proyecto para
  WordPress → Telegram.

Ninguno de los dos existe en código todavía. El roadmap
(`docs/ROADMAP.md`, `docs/roadmap/v1-roadmap.md`) construye primero el
núcleo de Commercial Manager y su dashboard (Sprint 3B-3C), y recién
después las integraciones de canal — Publication Inbox, Radar, WhatsApp
(Sprint 3D-3G) — porque el valor de negocio de administrar clientes y
campañas no depende de que ningún canal esté conectado todavía.

## Eventos de dominio (preparado, parcialmente implementado)

`core/events/` reserva el espacio donde vivirán los hechos de negocio que
la aplicación necesita comunicar entre agentes sin acoplarlos directamente
entre sí (por ejemplo: cuando WordPress crea un borrador, Analytics podría
querer enterarse sin que `agents/wordpress/` conozca la existencia de
`agents/analytics/`).

Hoy **no existe** ningún mecanismo de publicación/suscripción (event bus).
`NewsFound` tiene payload real desde Sprint 2, pero "dispararlo" hoy
significa simplemente devolverlo como resultado de
`DiscoveryEngine.run()` — quien lo reciba decide qué hacer. Los otros tres
eventos siguen siendo clases vacías. Se introducirá un
`core.ports.event_bus.EventBus` (contrato, igual que los demás ports) más
adelante en el roadmap, cuando exista un primer caso real de un agente
reaccionando al evento de otro — no antes.

Hasta entonces, `workflows/` sigue siendo el mecanismo previsto de
coordinación entre agentes (llamadas directas, secuenciales).

## Principios técnicos aplicados

- **SOLID**: cada agente tiene una única responsabilidad; se depende de
  abstracciones (`Protocol`), no de implementaciones concretas.
- **KISS**: sin capas que no resuelven un problema actual.
- **DRY**: configuración, logging y acceso a datos centralizados.
- **Tipado estricto**: `mypy --strict` en todo el código de producción.
