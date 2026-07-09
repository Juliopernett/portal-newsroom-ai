# Alcance del MVP

> El MVP se construye para un único cliente, Portal Vallenato, sin
> multi-tenencia. Este documento existe para que esa decisión sea
> explícita y consciente, no un olvido — ver
> [docs/product/SAAS_EVOLUTION.md](SAAS_EVOLUTION.md) para por qué esto no
> compromete la evolución futura de la plataforma.

## Dentro del MVP

Lo que Portal Vallenato necesita para que el sistema le ahorre tiempo,
como cliente único, con configuración global vía `.env`:

- Motor de descubrimiento (`DiscoveryEngine`) — **hecho, Sprint 2**.
- Persistencia del historial editorial, para deduplicar entre ejecuciones
  (no solo dentro de una pasada) — planeado, sprint "Persistence".
- Un `ContentSource` real (lector RSS) — planeado, sprint "RSS".
- Extracción de contenido completo — planeado, sprint "Extractor".
- Reescritura con IA, con el estilo editorial de Portal Vallenato
  configurado una sola vez — planeado, sprint "Writer".
- Creación de borradores en un único sitio WordPress — planeado, sprint
  "WordPress".
- Notificación por un único canal de Telegram — planeado, sprint
  "Telegram".
- Flujo de aprobación/rechazo humano, registrado en el historial.
- Propuestas básicas de contenido para redes sociales — planeado, sprint
  "Social".

## Fuera del MVP

Explícitamente diferido — no es que "no importe", es que construirlo
ahora sería resolver un problema que todavía no existe (un solo cliente
no necesita multi-tenencia):

- La entidad `MediaOutlet` y cualquier noción de "cliente" en el modelo
  de datos.
- Configuración por cliente vía interfaz — hoy toda la configuración es
  un `.env` que edita un ingeniero (ver
  [docs/product/CUSTOMER_CONFIGURATION.md](CUSTOMER_CONFIGURATION.md)).
- Más de un sitio WordPress, más de un canal de Telegram, más de un
  proveedor de IA seleccionable en tiempo de ejecución.
- Autenticación y cuentas de usuario — hoy no hay "usuarios del sistema",
  solo el equipo editorial de un único cliente.
- Facturación / suscripción.
- Cualquier API pública o panel de control — ver
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md) y
  [docs/ARCHITECTURE.md](../ARCHITECTURE.md): FastAPI sigue sin
  justificación mientras haya un solo cliente.
- `Publication`, `SocialAccount`, `AIProvider` y `NotificationChannel`
  como entidades de negocio explícitas (ver
  [docs/product/DOMAIN_MODEL.md](DOMAIN_MODEL.md)) — hoy son conceptos
  implícitos de un único cliente, no filas de una tabla.

## Versiones futuras

Ver [docs/ROADMAP.md](../ROADMAP.md), sección "Futuro — evolución hacia
SaaS", y el detalle completo en
[docs/product/SAAS_EVOLUTION.md](SAAS_EVOLUTION.md).

Resumen de a dónde apunta cada elemento diferido:

| Diferido en el MVP | Vuelve a aparecer en |
|---|---|
| `MediaOutlet` como entidad real | v1.1 — Multi-media support |
| Configuración por cliente | v1.2 — Customer configuration |
| Selección de proveedor de IA por cliente | v1.2 / v1.3 |
| Puntaje de relevancia de candidatos | v1.3 — AI scoring engine |
| Métricas por cliente | v1.4 — Analytics |
| Autenticación, facturación, API pública | v2.0 — True SaaS |

## Deuda técnica reconocida

Decisiones tomadas conscientemente para el MVP que **tendrán que
revisarse** cuando exista más de un cliente — no son errores, son
compromisos explícitos de alcance:

- `config/settings.py` es un único `Settings` global leído de un `.env`
  por proceso. Es la elección correcta para un cliente; para
  multi-tenencia real (v2.0) necesitará convivir con una fuente de
  configuración por cliente persistida — ver
  [docs/product/SAAS_EVOLUTION.md](SAAS_EVOLUTION.md), etapa "True SaaS".
- `DiscoveryEngine` deduplica solo dentro de una misma pasada (ver
  [docs/architecture/discovery-engine.md](../architecture/discovery-engine.md)) —
  la deduplicación persistente entre ejecuciones es del sprint
  "Persistence", todavía no del sprint "Discovery".
- Cobertura de tests: el código de Sprint 1 (`app/`, `database/engine.py`,
  varios `core/ports/*`) sigue sin pruebas — ver `CHANGELOG.md`, entrada
  0.3.0. No es deuda nueva de este reposicionamiento, pero sigue sin
  saldarse.
- El estilo editorial (tono, longitud, reglas) está hardcodeado como
  documentación (`docs/editorial/`), no como datos configurables — es
  correcto para un cliente único; se vuelve `EditorialRule` en v1.2.
