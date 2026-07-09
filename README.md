# Portal Newsroom AI

Plataforma interna de **Portal Vallenato** para asistir al equipo editorial en la
detección, redacción y publicación asistida de noticias.

> **Estado:** Fase 0 — Foundation. Todavía no hay agentes implementados.
> Ver [ROADMAP.md](docs/ROADMAP.md).

## ¿Qué es esto?

Portal Newsroom AI **no reemplaza al equipo editorial, lo asiste**. El sistema
detecta noticias, extrae contenido, lo reescribe con el estilo editorial del
medio, gestiona imágenes, prepara borradores en WordPress, genera contenido
para redes sociales y notifica al equipo por Telegram.

**El sistema nunca publica automáticamente.** Toda publicación requiere
aprobación humana. Ver [PROJECT_RULES.md](docs/PROJECT_RULES.md).

Para el contexto de negocio completo, ver [VISION.md](docs/VISION.md).
Para el diseño técnico, ver [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Product Vision

Portal Vallenato es el **cliente piloto**, no el producto final. Portal
Newsroom AI se diseña como una plataforma de inteligencia editorial
pensada para servir, a futuro, a múltiples medios digitales
independientes con necesidades editoriales comparables — sin que eso
retrase ni cambie el alcance del MVP que se está construyendo hoy para
Portal Vallenato.

Ver [docs/product/PRODUCT_VISION.md](docs/product/PRODUCT_VISION.md) para
la visión completa, y [docs/product/](docs/product/) para el modelo de
dominio, el alcance del MVP y la estrategia de evolución hacia SaaS.

## Stack tecnológico

- Python 3.13
- SQLite (MVP) → PostgreSQL (futuro)
- SQLAlchemy
- Pydantic / Pydantic Settings
- Playwright, BeautifulSoup, Requests
- WordPress REST API
- Telegram Bot API
- Docker
- Pytest, Ruff, Mypy

## Estructura del proyecto

```
app/          Composition root / entrypoint
core/         Dominio: entidades, eventos, servicios y contratos (ports)
agents/       Un paquete por responsabilidad (Radar, Extractor, Writer, ...)
workflows/    Composición de agentes en pipelines editoriales
database/     Persistencia (engine, modelos, repositorios)
config/       Configuración centralizada (.env)
shared/       Utilidades técnicas transversales (logging, ...)
prompts/      Plantillas de prompts de IA
scripts/      Scripts operativos puntuales
tests/        Pruebas unitarias e de integración
docs/         Documentación
docker/       Imagen de la aplicación
logs/         Logs en runtime
```

Detalle completo de cada carpeta en [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start

```bash
# 1. Clonar y crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements-dev.txt   # desarrollo: incluye producción + tests/lint/tipado
# pip install -r requirements.txt     # solo producción (esto es lo que usa docker/Dockerfile)

# 3. Configurar variables de entorno
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/Mac

# 4. Ejecutar pruebas
pytest

# 5. Ejecutar la aplicación (foundation smoke test)
python -m app.main
```

## Con Docker

```bash
docker compose up --build
```

## Project Documentation

Documentación completa del proyecto ("Engineering Handbook"), organizada
por tema. Si algo no está aquí, probablemente no está documentado
todavía.

**Base (Sprint 1 / 1.1):**

| Documento | Contenido |
|---|---|
| [VISION.md](docs/VISION.md) | Por qué existe el proyecto y qué problema resuelve |
| [ROADMAP.md](docs/ROADMAP.md) | Fases de desarrollo planeadas |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diseño técnico y decisiones de arquitectura |
| [PROJECT_RULES.md](docs/PROJECT_RULES.md) | Reglas no negociables del proyecto |
| [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Convenciones de código |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo contribuir |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |

**Visión de producto y evolución a SaaS** (ver [docs/product/](docs/product/)):

| Documento | Contenido |
|---|---|
| [product/PRODUCT_VISION.md](docs/product/PRODUCT_VISION.md) | Misión, visión, clientes objetivo, por qué no es un scraper ni un plugin de WordPress |
| [product/DOMAIN_MODEL.md](docs/product/DOMAIN_MODEL.md) | Entidades de negocio (incluye `MediaOutlet`) y sus relaciones |
| [product/MVP_SCOPE.md](docs/product/MVP_SCOPE.md) | Qué está dentro y fuera del MVP de Portal Vallenato |
| [product/SAAS_EVOLUTION.md](docs/product/SAAS_EVOLUTION.md) | Cómo se evoluciona de un cliente a una plataforma multi-cliente sin reescribir el sistema |
| [product/CUSTOMER_CONFIGURATION.md](docs/product/CUSTOMER_CONFIGURATION.md) | Todo lo que debería ser configurable por cliente a futuro |
| [product/COMPETITIVE_ADVANTAGES.md](docs/product/COMPETITIVE_ADVANTAGES.md) | En qué se diferencia de RSS readers, plugins de WordPress, Zapier y asistentes de IA simples |

**ADR — decisiones de arquitectura:**

| Documento | Contenido |
|---|---|
| [adr/ADR-001-project-vision.md](docs/adr/ADR-001-project-vision.md) | Por qué existe el proyecto, por qué no es un scraper, por qué agentes + Ports & Adapters |

**Architecture — diseño técnico con diagramas:**

| Documento | Contenido |
|---|---|
| [architecture/system-overview.md](docs/architecture/system-overview.md) | Visión general, flujo del sistema, agentes y responsabilidades (con diagramas Mermaid) |
| [architecture/discovery-engine.md](docs/architecture/discovery-engine.md) | Qué hace, qué no hace y cómo evolucionará el Discovery Engine |

**Business — el negocio detrás del código:**

| Documento | Contenido |
|---|---|
| [business/editorial-workflow.md](docs/business/editorial-workflow.md) | El flujo editorial completo, de la noticia a WordPress |

**Development — cómo se trabaja en este repo:**

| Documento | Contenido |
|---|---|
| [development/branch-strategy.md](docs/development/branch-strategy.md) | Git Flow: `feature/` → `develop` → `main` |
| [development/code-review.md](docs/development/code-review.md) | Qué se revisa antes de integrar un cambio |

**Deployment — hacia dónde va la infraestructura:**

| Documento | Contenido |
|---|---|
| [deployment/aws.md](docs/deployment/aws.md) | Estrategia de despliegue futura en AWS (propuesta, no implementada) |

**Editorial — principios que rigen el contenido:**

| Documento | Contenido |
|---|---|
| [editorial/style-guide.md](docs/editorial/style-guide.md) | Principios editoriales: sin inventar hechos, sin clickbait, SEO responsable, respeto por las fuentes |
| [editorial/ai-writing-rules.md](docs/editorial/ai-writing-rules.md) | Cómo debe escribir la IA: tono, longitud, fuentes, estilo |

**Operations — cómo se opera en producción:**

| Documento | Contenido |
|---|---|
| [operations/logging.md](docs/operations/logging.md) | Estrategia de logging actual y futura |

**Roadmap — el plan sprint a sprint:**

| Documento | Contenido |
|---|---|
| [roadmap/v1-roadmap.md](docs/roadmap/v1-roadmap.md) | Todos los sprints planeados hasta v1.0 (con diagrama) |

## Para desarrolladores nuevos

Para entender el proyecto en menos de una hora, lee en este orden:

1. [VISION.md](docs/VISION.md) — qué problema resuelve y qué NO es.
2. [adr/ADR-001-project-vision.md](docs/adr/ADR-001-project-vision.md) — por qué se tomaron las decisiones de arquitectura fundacionales.
3. [architecture/system-overview.md](docs/architecture/system-overview.md) — cómo está organizado, con diagramas.
4. [ARCHITECTURE.md](docs/ARCHITECTURE.md) — el mismo diseño, en detalle completo.
5. [PROJECT_RULES.md](docs/PROJECT_RULES.md) — lo que nunca se debe romper.
6. [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) — cómo se escribe el código aquí.
7. [business/editorial-workflow.md](docs/business/editorial-workflow.md) — el mismo sistema, visto desde el negocio.
8. [roadmap/v1-roadmap.md](docs/roadmap/v1-roadmap.md) — en qué sprint está el proyecto ahora mismo.

Luego, para saber dónde poner código nuevo, usa esta guía rápida:

| Quiero... | Voy a... |
|---|---|
| Agregar un nuevo agente | `agents/<nombre>/`, ver [CONTRIBUTING.md](CONTRIBUTING.md) |
| Definir un contrato del que dependa un agente | `core/ports/` |
| Modelar un concepto de negocio (Article, Source, ...) | `core/entities/` |
| Agregar lógica de negocio pura sin dueño claro | `core/services/` |
| Declarar un hecho de negocio ya ocurrido | `core/events/` |
| Encadenar varios agentes en un pipeline fijo | `workflows/` |
| Persistir algo | `database/models/` + `database/repositories/` |
| Agregar una variable de configuración | `config/settings.py` + `.env.example` |
| Ajustar el texto de un prompt de IA | `prompts/` |

## Licencia

Software propietario e interno de Portal Vallenato. Ver [LICENSE](LICENSE).
