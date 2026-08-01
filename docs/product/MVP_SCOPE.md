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
- **Commercial Manager** (`Client`, `CommercialContact`, `Contract`,
  `Plan`, `Campaign`, `PublicationRegistryEntry`, `Alert`) — agregado en
  Sprint 3A, planeado Sprint 3B (núcleo) y 3C (dashboard). No es
  multi-tenencia: todo `Client` vive dentro del único `MediaOutlet`
  implícito del MVP (Portal Vallenato) — ver
  [ADR-004](../adr/ADR-004-commercial-manager.md), Decisión 1, y
  [docs/architecture/commercial-manager.md](../architecture/commercial-manager.md).
- **Publication Inbox** (`PublicationRequest`, `MediaAsset`) — agregado en
  Sprint 3A, planeado Sprint 3D. Reemplaza a `NewsCandidate` como punto de
  entrada al pipeline editorial para todo canal (WhatsApp, Radar, manual)
  — ver [ADR-003](../adr/ADR-003-publication-inbox.md).
- **Autenticación, alcance mínimo** (`User`, `Session`) — agregado tras el
  deploy a Railway: la URL pública con datos sensibles de clientes
  (teléfonos, montos pagados) invalidó el supuesto de "solo corre en
  local" que justificaba dejar esto fuera. Login/logout/sesión con
  Argon2id, todos los endpoints protegidos, sin invitaciones, reset de
  contraseña, 2FA ni gestión de usuarios — ver
  [ADR-005](../adr/ADR-005-authentication.md) para el detalle completo y
  qué queda explícitamente para después.

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
- ~~Autenticación y cuentas de usuario~~ — **reincorporado al MVP tras el
  deploy a Railway**, alcance mínimo, ver ADR-005 arriba. Lo que sigue
  fuera: invitaciones, reset de contraseña, 2FA, bloqueo por intentos
  fallidos, roles/gestión avanzada de usuarios.
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
| Facturación, API pública | v2.0 — True SaaS |
| Roles, invitaciones, 2FA (autenticación *avanzada* — el login básico ya es MVP) | v1.2+ / según necesidad real |

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
