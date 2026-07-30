# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

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
