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

## Documentación

| Documento | Contenido |
|---|---|
| [VISION.md](docs/VISION.md) | Por qué existe el proyecto y qué problema resuelve |
| [ROADMAP.md](docs/ROADMAP.md) | Fases de desarrollo planeadas |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diseño técnico y decisiones de arquitectura |
| [PROJECT_RULES.md](docs/PROJECT_RULES.md) | Reglas no negociables del proyecto |
| [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Convenciones de código |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo contribuir |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |

## Para desarrolladores nuevos

Para entender el proyecto en menos de 30 minutos, lee en este orden:

1. [VISION.md](docs/VISION.md) — qué problema resuelve y qué NO es.
2. [ARCHITECTURE.md](docs/ARCHITECTURE.md) — cómo está organizado y por qué.
3. [PROJECT_RULES.md](docs/PROJECT_RULES.md) — lo que nunca se debe romper.
4. [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) — cómo se escribe el código aquí.
5. [ROADMAP.md](docs/ROADMAP.md) — en qué fase está el proyecto ahora mismo.

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
