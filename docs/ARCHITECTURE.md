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

- `core/entities/`: modelos de dominio (se poblará a partir de la Fase 1,
  cuando exista un agente que realmente los necesite).
- `core/ports/`: contratos (`typing.Protocol`) que describen lo que cada
  agente necesita de una fuente de contenido, un extractor, un proveedor de
  IA, un proveedor de imágenes, un publicador de CMS, un notificador y un
  repositorio de persistencia/historial.
- `core/events/`: eventos de dominio — hechos de negocio ya ocurridos
  (`NewsFound`, `ArticleRewritten`, `DraftCreated`,
  `NotificationRequested`). Hoy son clases vacías; tendrán payload real a
  partir de Sprint 2. Ver "Eventos de dominio" más abajo.
- `core/services/`: servicios de dominio — lógica de negocio pura que no
  pertenece a una única entidad (ver `core/services/README.md`).
- `core/exceptions.py`: jerarquía de errores de negocio
  (`DomainError` y subclases).

### `agents/` — Aplicación (casos de uso)

Un paquete por responsabilidad. Cada agente depende únicamente de los
`ports` de `core/` que necesita, nunca de un adaptador concreto:

| Agente | Responsabilidad | Port principal |
|---|---|---|
| `radar` | Detectar noticias nuevas | `ContentSource`, `Repository` |
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

## Eventos de dominio (preparado, no implementado)

`core/events/` reserva el espacio donde vivirán los hechos de negocio que
la aplicación necesita comunicar entre agentes sin acoplarlos directamente
entre sí (por ejemplo: cuando WordPress crea un borrador, Analytics podría
querer enterarse sin que `agents/wordpress/` conozca la existencia de
`agents/analytics/`).

Hoy **no existe** ningún mecanismo de publicación/suscripción (event bus).
Los eventos son solo clases vacías, documentadas, sin comportamiento. Esto
es intencional: se introducirá un `core.ports.event_bus.EventBus` (contrato,
igual que los demás ports) más adelante en el roadmap, cuando exista un
primer caso real de un agente reaccionando al evento de otro — no antes.

Hasta entonces, `workflows/` sigue siendo el único mecanismo de
coordinación entre agentes (llamadas directas, secuenciales).

## Principios técnicos aplicados

- **SOLID**: cada agente tiene una única responsabilidad; se depende de
  abstracciones (`Protocol`), no de implementaciones concretas.
- **KISS**: sin capas que no resuelven un problema actual.
- **DRY**: configuración, logging y acceso a datos centralizados.
- **Tipado estricto**: `mypy --strict` en todo el código de producción.
