# Estándares de código

## Formato y estilo

- Formateo y linting con **Ruff** (`ruff format`, `ruff check`).
  Configuración en `pyproject.toml`. Longitud de línea: 100 caracteres.
- Orden de imports: librería estándar → terceros → primer partido
  (`app`, `core`, `agents`, `workflows`, `database`, `config`, `shared`),
  aplicado automáticamente por Ruff (regla `I`).
- Sin `except:` desnudo. Capturar excepciones específicas o
  `DomainError`/subclases definidas en `core/exceptions.py`.

## Tipado

- `mypy --strict` sobre todo el código de producción (excluye `tests/`).
- Toda función pública declara tipos de parámetros y retorno.
- Evitar `Any`; si es inevitable, justificarlo con un comentario breve.
- Usar `Protocol` (no `ABC`) para definir contratos en `core/ports/`, salvo
  que se necesite lógica compartida en la clase base.

## Nombres

- `snake_case` para funciones, variables y módulos.
- `PascalCase` para clases.
- `UPPER_SNAKE_CASE` para constantes.
- Nombres explícitos y en el vocabulario del negocio: `articulo`,
  `borrador`, `fuente`, `duplicado` — evitar abreviaturas como `art`, `bdr`.
- Un archivo, una responsabilidad. Si un archivo mezcla más de un concepto,
  se divide.

## Documentación en código

- Toda función, clase o método público lleva docstring explicando **qué**
  hace y, si no es evidente, **por qué**. No se documenta el "cómo" —
  eso lo explica el propio código.
- Los módulos placeholder (agentes aún no implementados) documentan su
  responsabilidad futura en un `README.md` dentro de su propia carpeta.

## Comentarios

- Comentarios solo cuando el código no puede explicarse a sí mismo: una
  decisión no obvia, una limitación de una librería externa, un workaround
  temporal (indicando por qué es necesario).
- No se documenta el qué (eso ya lo dice el código), ni se referencia la
  tarea o el prompt que originó el cambio — eso vive en el commit y en
  `CHANGELOG.md`.

## Estructura de módulos

- `core/` no importa nada de `agents/`, `database/`, `app/` ni librerías de
  terceros orientadas a infraestructura (SQLAlchemy, requests, Playwright).
- `agents/<nombre>/` no importa directamente otro paquete de `agents/`; si
  dos agentes necesitan coordinarse, esa coordinación vive en `workflows/`.
- Los adaptadores concretos (WordPress, Telegram, proveedor de IA) implementan
  un `Protocol` de `core/ports/` y viven junto al agente que los usa o en
  `database/repositories/` si son de persistencia.
- No se crean módulos genéricos (`utils.py`, `helpers.py`, `common.py`).
  Cada utilidad vive en un módulo nombrado según lo que hace (ejemplo:
  `shared/logger.py`, no `shared/utils.py`). Si una utilidad no tiene un
  nombre específico y claro, probablemente no está lista para extraerse
  todavía — déjala donde se usa hasta que lo tenga.

## Eventos de dominio

- Cada evento en `core/events/` se nombra en pasado y describe un hecho de
  negocio que **ya ocurrió** (`NewsFound`, `DraftCreated`), nunca una orden
  o comando (evitar `CreateDraft`, `SendNotification`).
- Un archivo por evento. El nombre del archivo es el nombre de la clase en
  `snake_case` (`news_found.py` → `NewsFound`).
- Los eventos no implementan comportamiento ni dependen de infraestructura;
  son datos inmutables. La lógica que reacciona a un evento vive en quien
  lo consume, no en el evento mismo.

## Servicios de dominio

- Un servicio en `core/services/` es una función o clase sin estado que
  implementa lógica de negocio que no pertenece naturalmente a una sola
  entidad. Ver `core/services/README.md`.
- Recibe sus dependencias ya resueltas contra los `ports` de `core/ports/`
  — nunca instancia un adaptador concreto por su cuenta.

## Pruebas

- Un archivo de test por módulo de producción, reflejando su ubicación
  (`agents/writer/` → `tests/unit/agents/writer/`).
- Un comportamiento por test. Nombres descriptivos:
  `test_<qué_se_prueba>_<condición_esperada>`.
- Preferir fixtures de `pytest` sobre `setUp`/`tearDown` estilo `unittest`.
- Las pruebas unitarias no deben requerir red, credenciales ni servicios
  externos reales — se prueban contra los `ports`, no contra los adaptadores.

## Commits

Seguir [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
