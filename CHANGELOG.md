# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

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

[Unreleased]: https://example.invalid/compare/v0.2.0...HEAD
[0.2.0]: https://example.invalid/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.invalid/releases/v0.1.0
