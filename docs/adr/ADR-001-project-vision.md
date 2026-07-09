# ADR-001: Visión del proyecto y decisiones fundacionales de arquitectura

- **Estado:** Aceptado
- **Fecha:** 2026-07-07 (Sprint 1 — Foundation)
- **Contexto del documento:** este es un *Architecture Decision Record*
  (ADR): un registro corto de una decisión de diseño, su contexto y sus
  consecuencias, escrito en el momento en que se tomó — no un documento
  que se reescribe a medida que cambian de opinión. Si una decisión de
  aquí cambia en el futuro, se documenta en un ADR nuevo que referencia a
  este, no editando este archivo.

## Contexto

Portal Vallenato es un medio de comunicación regional. Su equipo editorial
dedica una parte significativa del día a tareas mecánicas y repetitivas:
detectar noticias relevantes, extraer su contenido, reescribirlas con el
estilo del medio, conseguir y preparar imágenes, crear el borrador en
WordPress, redactar copys para redes sociales y coordinar al equipo. Ese
tiempo se resta del trabajo que sí requiere criterio humano: verificar
fuentes, decidir enfoque editorial y garantizar calidad periodística.

Ver [docs/VISION.md](../VISION.md) para el planteamiento completo del
problema de negocio.

## Decisión 1 — Qué problema resuelve Portal Newsroom AI

Construimos un sistema de **agentes especializados** que automatiza el
trabajo mecánico del flujo editorial (detectar, extraer, reescribir,
gestionar imágenes, preparar borrador, notificar) y deja al equipo humano
el trabajo de criterio: revisar, corregir y aprobar. El objetivo es
**ahorrar tiempo**, no **reemplazar juicio editorial**.

## Decisión 2 — Por qué no es un scraper

Un scraper es una herramienta que extrae y republica contenido. Portal
Newsroom AI **nunca publica automáticamente** — esa es la regla más
importante del proyecto (ver
[docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 1). El resultado
máximo que cualquier pipeline automatizado puede producir es un
**borrador** más una **notificación** al equipo editorial; la publicación
final es siempre una acción humana explícita en WordPress.

Esta distinción no es cosmética: cambia el diseño del sistema entero.
Un scraper optimiza para velocidad y volumen. Portal Newsroom AI optimiza
para que un editor humano tenga, en el menor tiempo posible, todo lo que
necesita para decidir con criterio — y nunca elimina ese punto de
decisión humano del flujo.

## Decisión 3 — Por qué una arquitectura por agentes

En vez de un único programa monolítico que "hace todo", el sistema se
divide en agentes de una sola responsabilidad (Radar, Extractor, Writer,
SEO, Images, WordPress, Telegram, Scheduler, Social, Analytics, AI
Orchestrator — ver
[docs/architecture/system-overview.md](../architecture/system-overview.md)).

Razones:

- **Reemplazabilidad.** Si mañana cambiamos WordPress por otro CMS, o
  dejamos de usar Telegram, el cambio queda contenido en un solo agente.
- **Comprensibilidad.** Un desarrollador nuevo puede entender y modificar
  un agente sin cargar mentalmente el pipeline completo.
- **Evolución incremental.** Cada agente entrega valor por sí solo — el
  proyecto no necesita estar "completo" para ser útil (ver
  [docs/roadmap/v1-roadmap.md](../roadmap/v1-roadmap.md)).
- **Testabilidad.** Cada agente se prueba de forma aislada, sin depender
  de que los demás estén implementados o de servicios externos reales.

## Decisión 4 — Por qué Ports & Adapters (arquitectura hexagonal)

Los agentes no llaman directamente a librerías de infraestructura
(WordPress REST API, Telegram Bot API, un proveedor de IA, SQLAlchemy).
Llaman a **contratos** (`typing.Protocol`) definidos en `core/ports/`. Las
integraciones concretas son **adaptadores** que implementan esos
contratos.

Esto resuelve directamente la Decisión 3: la reemplazabilidad de un
agente solo es real si ese agente no conoce los detalles de la librería
externa que usa hoy. Ports & Adapters es el patrón estándar para lograr
eso sin inventar nada propio, y es consistente con Clean Architecture:
las dependencias siempre apuntan hacia adentro, hacia `core/`, nunca al
revés.

Ver el detalle técnico completo, capa por capa, en
[docs/ARCHITECTURE.md](../ARCHITECTURE.md).

## Consecuencias

- Cada nuevo agente requiere, como mínimo, decidir qué `port` necesita
  antes de escribir código de infraestructura — esto es intencional, no
  fricción accidental.
- `core/` se mantiene libre de dependencias externas (SQLAlchemy,
  Playwright, requests, SDKs de terceros) — ver
  [docs/CODING_STANDARDS.md](../CODING_STANDARDS.md).
- No se introduce FastAPI, un event bus, ni microservicios hasta que un
  sprint concreto lo necesite — ver [docs/PROJECT_RULES.md](../PROJECT_RULES.md)
  y la sección "Eventos de dominio" de [docs/ARCHITECTURE.md](../ARCHITECTURE.md).
