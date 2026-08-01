# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added

- **Mejoras UX P0 (Sprint 3F)**: los 5 hallazgos P0 de
  `docs/ux/sprint-3d5-ux-review.md`, implementados solo en
  `app/api/static/` (HTML/CSS/JS) — cero cambios de backend, dominio o
  reglas de negocio; los umbrales nuevos son decisiones de presentación,
  no persisten en ningún lado ni afectan a la API.
  - Barra de resumen (`#resumen`) visible en ambas pestañas: solicitudes
    pendientes, pautas por vencer (≤7 días) y cupos agotados —
    recalculada en cada carga de datos.
  - Badges nuevos en la pestaña Clientes y Pautas: "vence en Nd" (además
    del "vencida" existente) y "cupo bajo (N)" (≤2 restantes, distinto de
    "cupo agotado", que ya existía).
  - Solicitudes con ≥4 horas esperando se resaltan en la cola (ícono de
    reloj + borde de color) — no bloquean ni alteran el orden, solo
    llaman la atención.
  - "Nuevo cliente" y "Nueva pauta" ahora son `<details>` colapsados por
    defecto (se re-colapsan solos tras crear con éxito), para que la
    lista de clientes sea lo primero visible en esa pestaña.
  - Verificado con datos reales contra el servidor corriendo (pauta a 3
    días de vencer, pauta con 2 restantes, pauta agotada, solicitud
    reforzada 6h atrás directamente en la base para simular espera) — la
    extensión de navegador se desconectó a mitad de la verificación
    (requiere reautenticación, ajeno a este cambio) así que la
    confirmación final se hizo ejecutando la lógica real de `app.js`
    (extraída del archivo que el servidor sirve, no una reimplementación)
    contra las respuestas reales de la API en Node, más inspección directa
    del HTML/CSS servidos.
  - Con este sprint se cierra el desarrollo de funcionalidades nuevas a
    propósito: el sistema queda en uso real varios días antes de
    continuar con las mejoras P1, WhatsApp, IA o automatizaciones.

- **Cerrar el flujo operativo: vincular pauta (Sprint 3E)**: una
  `PublicationRequest` recibida sin `Pauta` ahora puede vincularse
  después, antes de aceptarse/publicarse — el hallazgo P2 más importante
  de `docs/ux/sprint-3d5-ux-review.md`, cerrado antes de continuar con
  las mejoras visuales (P0/P1) de ese mismo documento.
  - `core.services.publication_request_service.link_pauta`: transición
    inmutable que fija `pauta_id` sin tocar `estado` — cero reglas de
    negocio nuevas, mismo patrón que `mark_as_published`.
  - `POST /publication-requests/{id}/link-pauta` (`pauta_id` en el
    cuerpo) — 404 si la solicitud no existe, 400 si la pauta no existe
    (constraint de FK, mismo mecanismo que el resto de la API), 200 con
    la solicitud actualizada.
  - UI: las filas de la cola sin pauta ahora muestran un selector +
    botón "Vincular" en vez de un botón "Publicar" deshabilitado; al
    vincular, la fila se refresca y el botón "Publicar" queda
    disponible. Verificado en navegador real: solicitud sin pauta →
    vincular → publicar → cupo restante de la pauta baja correctamente.
  - Deliberadamente fuera de este sprint: la barra de resumen, los
    badges "por vencer", el resaltado de solicitudes urgentes y los
    formularios colapsados (P0/P1 de la revisión UX) — quedan para el
    siguiente sprint, ahora que el flujo que representan está completo.

- **Excel-replacement UI (Sprint 3D-UI)**: interfaz mínima en
  `app/api/static/` — una sola página HTML, sin framework ni build step,
  servida por el mismo FastAPI en `/ui/` (sin CORS). Dos pantallas: **Cola
  de Solicitudes** (registrar, ver pendientes, publicar) y **Clientes y
  Pautas** (crear cliente, crear pauta, ver cupo/vigencia por cliente).
  Probado de punta a punta en un navegador real: crear cliente → crear
  pauta → registrar 1 solicitud → publicarla → confirmar que el cupo
  restante bajó de 10/10 a 9/10.
  - Se descubrió que la API (Sprint 3D) no tenía ningún endpoint de
    lectura en lista — solo creación y `GET /pautas/{id}` uno por uno.
    Sin eso, ninguna pantalla podía mostrar qué existe. Se agregaron
    exactamente 3, autorizados explícitamente antes de implementarlos:
    `GET /clients`, `GET /pautas` (con cupo/vigencia calculados,
    reutilizando `PautaService`), `GET /publication-requests` (filtro
    opcional `estado`). Ningún otro endpoint resultó necesario.
  - Nuevo en los puertos/repositorios: `ClientRepository.list_all`,
    `PublicationRequestRepository.list_all(estado=None)` — puro acceso de
    lectura sobre datos ya existentes, cero reglas de negocio nuevas.
    `PautaRepository.list_all` ya existía desde Sprint 3C, sin cambios.
  - `GET /` redirige a `/ui/` para que abrir la URL base ya muestre la
    interfaz.

- **Internal API (Sprint 3D)**: API REST mínima en `app/api/` sobre el
  Commercial Core (`Client`, `Pauta`, `PublicationRequest`) — primera
  forma de operar el dominio sin escribir Python. Sin autenticación, sin
  permisos, sin paginación, sin filtros avanzados, sin OpenAPI
  personalizado (docs automáticas de FastAPI en `/docs`, sin tocar).
  - `POST /clients`, `POST /pautas`, `GET /pautas/{id}` (con
    `publicaciones_consumidas`/`restantes`/`vigente`/`vencida`/
    `cuota_agotada` calculados vía `PautaService`, sin lógica nueva),
    `POST /publication-requests`.
  - `POST /publication-requests/{id}/publish`: no estaba en la lista
    literal del sprint, pero sin ella `GET /pautas/{id}` nunca mostraría
    cupo consumido — expone `mark_as_published` (Sprint 3B), cero lógica
    de dominio nueva.
  - `app/api/dependencies.py`: un `UnitOfWork` por request vía FastAPI
    `Depends`; `app/api/errors.py`: `ValueError` de una entidad → 422,
    `IntegrityError` de una FK violada → 400, sin try/except repetido en
    cada handler.
  - `database/engine.py`: `enable_sqlite_foreign_keys` — SQLite no aplica
    llaves foráneas por defecto (a diferencia de Postgres); sin esto, un
    `client_id`/`pauta_id` inválido pasaría silencioso en dev/tests y
    fallaría recién en producción. Esto rompió cuatro tests de Sprint 3C
    que usaban IDs inventados sin fila real — se corrigieron para crear
    las entidades padre de verdad, como ya haría Postgres.
  - `fastapi`, `uvicorn[standard]` en `requirements.txt`; `httpx` (para
    `TestClient`) en `requirements-dev.txt`.
  - `tests/integration/api/`: un test por endpoint más un flujo completo
    de extremo a extremo por HTTP (crear cliente → pauta → 3 solicitudes
    → publicar 2 → verificar 8 restantes) — el mismo escenario de la
    Definición de Terminado de Sprint 3B, ahora sobre HTTP real.

- **Persistence Layer (Sprint 3C)**: `Client`, `Pauta` y `PublicationRequest`
  ahora se pueden persistir en PostgreSQL (Railway) o SQLite, sin cambiar
  el dominio.
  - `core/ports/`: `ClientRepository`, `PautaRepository` (+ `list_all`),
    `PublicationRequestRepository` (+ `list_by_pauta_id`) — contratos
    mínimos, cada método respaldado por una necesidad real del dominio, no
    heredan del `Repository[T]` genérico (reservado para Discovery).
    `UnitOfWork` (`ABC`, no `Protocol` — comparte lógica real de
    commit/rollback en la clase base).
  - `database/models/`: `ClientModel`, `PautaModel`,
    `PublicationRequestModel` — mapeos SQLAlchemy 2.0 (Declarative
    Mapping), completamente separados de las entidades de dominio;
    `pauta_id` nullable, reflejando el ajuste de Sprint 3B.1. `tipo`/
    `estado` se guardan como `String` simple, nunca `ENUM` nativo de
    Postgres (evita migraciones costosas al agregar un valor nuevo).
  - `database/repositories/`: `SqlAlchemyClientRepository`,
    `SqlAlchemyPautaRepository`, `SqlAlchemyPublicationRequestRepository`
    — traducen entidad ↔ modelo ORM.
  - `database/unit_of_work.py`: `SqlAlchemyUnitOfWork` — una transacción
    por bloque `with`, rollback automático al salir salvo `commit()`
    explícito.
  - `database/engine.py`: `normalize_database_url` — reescribe
    `postgres://` (lo que Railway entrega) a `postgresql+psycopg://` (lo
    que SQLAlchemy 2.0 requiere).
  - Alembic inicializado en `database/migrations/`; migración inicial
    generada y verificada con un ciclo completo `upgrade head` →
    `downgrade base` → `upgrade head` (reconstruye el esquema desde cero)
    y `alembic check` (sin drift entre modelos y migración).
  - `psycopg[binary]` agregado a `requirements.txt`.
  - Motor síncrono, no asíncrono — decisión explícita: nada en el proyecto
    hoy es async (agentes, `DiscoveryEngine`, futuro `app/`), y no hay
    carga concurrente que lo justifique.
  - Tests de persistencia (`tests/integration/persistence/`) corren
    contra SQLite local, no contra Railway real — sin acceso a esas
    credenciales desde este entorno. El esquema evita deliberadamente
    cualquier característica exclusiva de Postgres para que el mismo
    código se comporte igual en ambos.

### Changed

- **Domain Adjustment (Sprint 3B.1)**: `PublicationRequest.pauta_id` pasa
  de obligatorio a opcional (`str | None`). Ahora puede existir una
  solicitud sin `Pauta` asignada mientras esté en `RECIBIDA` o
  `CANCELADA` — la obligatoriedad se traslada al momento de pasar a
  `ACEPTADA` o `PUBLICADA`, validado por la propia entidad. Corrige la
  discrepancia señalada en la revisión de dominio de Sprint 3B: el modelo
  anterior no podía representar el caso operativo más común (un mensaje
  de WhatsApp de un remitente aún sin vincular a un cliente).

### Added

- **Commercial Core MVP (Sprint 3B)**: primer código real del dominio
  comercial, reemplaza al Excel que usa hoy Portal Vallenato para
  controlar pautas. Basado en Domain Discovery sobre reglas de negocio
  reales, no en el diseño especulativo de Sprint 3A (ver nota en
  "Changed" abajo).
  - `core.entities.client.Client` (+ `ClientType`): el cliente comercial
    (artista, manager, promotor, empresario).
  - `core.entities.pauta.Pauta`: un período comercial contratado —
    cantidad de publicaciones, fecha de inicio/fin propias del cliente
    (nunca calendario), valor y fecha de pago.
  - `core.entities.publication_request.PublicationRequest` (+
    `PublicationRequestStatus`): una solicitud recibida por WhatsApp,
    vinculada a una `Pauta`. Sin adjuntos todavía (sprint futuro).
  - `core.services.pauta_service.PautaService`: publicaciones
    consumidas/restantes, vigencia/vencimiento y cuota agotada de una
    `Pauta` — todo calculado a partir del historial de
    `PublicationRequest`, nunca un contador almacenado. Reloj inyectable
    para tests, mismo patrón que `DiscoveryEngine`.
  - `core.services.publication_request_service.mark_as_published`: la
    transición de estado inmutable de una `PublicationRequest`.
  - Tests unitarios (entidades + servicios) e integración
    (`tests/integration/test_commercial_core_scenario.py`, el escenario
    completo de la Definición de Terminado del sprint) — 100% de
    cobertura en todo el código nuevo, mismo estándar que Discovery
    Engine (Sprint 2).
- Reposicionamiento comercial (Sprint 3A): la mayoría de las publicaciones
  de Portal Vallenato no se originan en Discovery, llegan por WhatsApp de
  managers, artistas y empresas. Documentado en
  [ADR-003](docs/adr/ADR-003-publication-inbox.md) (bounded context
  **Publication Inbox**, entidad `PublicationRequest` como convergencia de
  cualquier canal de entrada) y
  [ADR-004](docs/adr/ADR-004-commercial-manager.md) (bounded context
  **Commercial Manager**: `Client`, `CommercialContact`, `Contract`,
  `Plan`, `Campaign`, `PublicationRegistryEntry`, `Alert`).
- `docs/architecture/publication-inbox.md` y
  `docs/architecture/commercial-manager.md`: diseño técnico de ambos
  bounded contexts.
- `docs/business/commercial-workflow.md`: el flujo comercial visto desde
  negocio, complementa a `docs/business/editorial-workflow.md`.
- `agents/whatsapp/README.md`: placeholder documentado para el futuro
  agente/canal WhatsApp.
- `docs/ROADMAP.md` (Fase 1.5) y `docs/roadmap/v1-roadmap.md`: seis
  sprints nuevos (Commercial Manager Core, Commercial Dashboard,
  Publication Inbox Core, Radar → Publication Inbox, WhatsApp Channel,
  Commercial Registry Wiring), en ese orden — núcleo comercial y su
  dashboard antes que las integraciones de canal.
- `docs/product/DOMAIN_MODEL.md`: entidades `PublicationRequest`,
  `MediaAsset`, `Client`, `CommercialContact`, `Contract`, `Plan`,
  `Campaign`, `PublicationRegistryEntry`, `Alert`, con la disambiguación
  explícita `Client` vs. `MediaOutlet`.
- `docs/product/MVP_SCOPE.md`: Commercial Manager y Publication Inbox
  entran al alcance del MVP de Portal Vallenato (sin introducir
  multi-tenencia — ver ADR-004, Decisión 1).

### Changed

- **Nota de divergencia (Sprint 3B):** el código de Commercial Core MVP
  descrito arriba implementa un dominio más simple que el diseñado en
  Sprint 3A / ADR-003 / ADR-004. `CommercialContact`, `Contract`, `Plan`,
  `Campaign`, `Alert` y "Publication Inbox" como bounded context
  multicanal **no se implementaron** — no tenían respaldo en las reglas
  de negocio reales relevadas en Domain Discovery (Sprint 3B). Los ADR-003
  y ADR-004, y la documentación que actualizan, describen una fase de
  diseño ya superada por el código; quedan como registro histórico, no
  como especificación vigente. Actualizar esa documentación queda
  pendiente de un sprint dedicado a ese fin.
- `docs/VISION.md`, `docs/product/PRODUCT_VISION.md`,
  `docs/business/editorial-workflow.md`,
  `docs/architecture/system-overview.md`, `docs/ARCHITECTURE.md`,
  `agents/radar/README.md` y `README.md` anotados (sin reescribir su
  contenido original) para reflejar que Radar es uno de varios canales de
  entrada, no el único.

## [0.3.0] - 2026-07-08

### Added

- Entidades de dominio en `core/entities/`: `NewsCandidate`, `Source`,
  `Article` (con `ArticleStatus`), `EditorialTask` (con
  `EditorialTaskStatus`) — dataclasses inmutables, sin dependencias
  externas.
- `core.services.deduplication.generate_candidate_hash`: huella de
  contenido usada para deduplicar candidatos.
- `core.services.discovery_engine.DiscoveryEngine`: agrega, deduplica por
  hash y ordena candidatos de varias fuentes; devuelve un evento
  `NewsFound`.
- `tests/fakes/FakeContentSource`: doble de prueba que lee fixtures JSON
  en lugar de la red, implementando `core.ports.content_source.ContentSource`.
- `tests/fixtures/{silvestre,churo,festival}.json`: noticias vallenatas de
  ejemplo, con un duplicado intencional para probar la deduplicación.
- 41 pruebas nuevas (unitarias sobre entidades/servicios con dobles en
  memoria, de integración sobre fixtures reales). 100% de cobertura sobre
  el código nuevo de este sprint.
- `exclude_lines` en `[tool.coverage.report]` (`pyproject.toml`) para no
  penalizar cuerpos de método de `Protocol` (nunca se ejecutan
  directamente) en el cálculo de cobertura.

### Changed

- `core.ports.content_source.ContentSource`: `fetch_new_references() ->
  list[str]` pasa a ser `fetch_candidates() -> list[NewsCandidate]`, y
  gana una propiedad `source: Source`. Ningún adaptador implementaba
  todavía este port, así que no rompe nada en ejecución — es la
  formalización que el propio docstring del port anticipaba desde Sprint 1.
- `core.events.news_found.NewsFound` pasa de ser una clase vacía a tener
  payload real (`candidates`, `occurred_at`).

## [0.2.0] - 2026-07-07

### Added

- `core/events/`: espacio reservado para eventos de dominio (`NewsFound`,
  `ArticleRewritten`, `DraftCreated`, `NotificationRequested`) — clases
  vacías y documentadas, sin comportamiento ni event bus todavía.
- `core/services/`: espacio reservado para servicios de dominio, con
  `README.md` explicando qué pertenece y qué no pertenece ahí.
- `requirements-dev.txt`: dependencias de desarrollo (testing, lint,
  tipado) separadas de `requirements.txt` (producción).
- Configuración de `coverage` (`pytest-cov`) en `pyproject.toml`.
- Plugin de mypy para Pydantic (`pydantic.mypy`) en `pyproject.toml`.
- Sección "Para desarrolladores nuevos" en `README.md` con ruta de lectura
  y guía de "dónde poner código nuevo".
- Regla de estilo contra módulos `utils.py`/`helpers.py` genéricos y
  convenciones de nombrado para eventos y servicios de dominio en
  `docs/CODING_STANDARDS.md`.
- Sección "Eventos de dominio (preparado, no implementado)" en
  `docs/ARCHITECTURE.md`.

### Changed

- `requirements.txt` ya no incluye herramientas de desarrollo (`pytest`,
  `ruff`, `mypy`) — antes se instalaban también en la imagen Docker de
  producción sin necesidad.
- `docker/Dockerfile` ahora instala una imagen de producción más liviana
  como efecto de lo anterior (sin cambios en el propio Dockerfile).

### Fixed

- Referencias desactualizadas en `README.md` (`core/` ya no se describía
  con precisión tras esta revisión).

## [0.1.0] - 2026-07-07

### Added

- Estructura base del proyecto (Prompt 001 — Foundation): `app/`, `core/`,
  `agents/`, `workflows/`, `database/`, `config/`, `shared/`, `prompts/`,
  `scripts/`, `tests/`, `docs/`, `docker/`, `logs/`.
- Esqueleto de arquitectura hexagonal: contratos (`Protocol`) en
  `core/ports/` y excepciones de dominio en `core/exceptions.py`.
- Paquetes placeholder documentados para los futuros agentes: Radar,
  Extractor, Writer, SEO, Images, WordPress, Telegram, Scheduler, Social,
  Analytics y AI Orchestrator.
- Configuración centralizada vía `config/settings.py` (Pydantic Settings +
  `.env`).
- Logging centralizado vía `shared/logger.py`.
- Scaffolding de base de datos (engine y sesión de SQLAlchemy) en
  `database/`, sin modelos todavía.
- Configuración de Docker (`docker/Dockerfile`, `docker-compose.yml`).
- Documentación de proyecto: `README.md`, `VISION.md`, `ROADMAP.md`,
  `ARCHITECTURE.md`, `PROJECT_RULES.md`, `CODING_STANDARDS.md`,
  `CONTRIBUTING.md`.
- Suite inicial de pruebas (`pytest`) validando la carga de configuración.

[Unreleased]: https://example.invalid/compare/v0.3.0...HEAD
[0.3.0]: https://example.invalid/compare/v0.2.0...v0.3.0
[0.2.0]: https://example.invalid/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.invalid/releases/v0.1.0
