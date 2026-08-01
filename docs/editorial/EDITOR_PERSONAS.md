# Roles editoriales

> Roles humanos que interactúan con la plataforma. Corresponde a la
> entidad conceptual `Editor` de
> [docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md) — hoy no
> existe distinción de roles en código (hay un único equipo editorial
> implícito, ver [docs/product/MVP_SCOPE.md](../product/MVP_SCOPE.md)).
> Este documento define esos roles a nivel funcional, antes de que exista
> autenticación o permisos para hacerlos cumplir.

## Los roles

### Editor Jefe (Editor-in-Chief)

**Responsabilidad:** supervisión editorial general. Define y ajusta las
reglas editoriales del medio (tono, prioridades, qué fuentes son
confiables) — la contraparte humana de `EditorialRule` en
[docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md). Resuelve
casos ambiguos que un editor no se anima a decidir solo. Revisa
[KPIS.md](KPIS.md) para entender si el equipo y la plataforma están
funcionando bien juntos, no interviene artículo por artículo salvo
excepción.

**Permisos futuros:** administrar `EditorialRule`, agregar o desactivar
`Source`, ver métricas agregadas de todo el equipo.

### Editor

**Responsabilidad:** el rol operativo diario — revisa las notificaciones
de candidatos (ver
[EDITORIAL_DECISION_TREE.md](EDITORIAL_DECISION_TREE.md)), aprueba,
rechaza o pide cambios sobre borradores, y publica manualmente en
WordPress lo que aprueba. Es quien resuelve la mayoría de las
`EditorialTask`.

**Permisos futuros:** aprobar/rechazar artículos, editar borradores,
publicar, confirmar o descartar rumores (ver
[EDITORIAL_POLICIES.md](EDITORIAL_POLICIES.md), EP-04).

### Editor de Redes (Social Media Editor)

**Responsabilidad:** revisa y aprueba las propuestas de contenido para
redes sociales que genera el futuro agente Social, una vez que un
artículo ya está publicado. No interviene en la aprobación del artículo
en sí — su punto de decisión es posterior, ver
[NEWS_LIFECYCLE.md](NEWS_LIFECYCLE.md), estado `Shared`.

**Permisos futuros:** aprobar/editar/rechazar propuestas de redes,
administrar `SocialAccount` (ver
[docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md)).

### Periodista (Journalist)

**Responsabilidad:** puede escribir o editar contenido directamente,
más allá de revisar lo que la IA propone — cubre el caso de una nota que
un periodista redacta desde cero, no a partir de un `NewsCandidate`
detectado automáticamente. No necesariamente tiene permiso de aprobación
final (eso depende de si también es Editor).

**Permisos futuros:** crear y editar `Article` directamente, enviarlo a
revisión de un Editor.

### Administrador (Administrator)

**Responsabilidad:** configuración técnica y de cuenta del cliente — no
un rol editorial en sí. Administra credenciales (WordPress, Telegram,
proveedor de IA — ver
[docs/product/CUSTOMER_CONFIGURATION.md](../product/CUSTOMER_CONFIGURATION.md)),
gestiona qué personas tienen cada rol.

**Permisos futuros:** todo lo anterior, más gestión de usuarios y
configuración de integraciones. En el modelo SaaS futuro
(ver [docs/product/SAAS_EVOLUTION.md](../product/SAAS_EVOLUTION.md)),
este rol es el punto de contacto de un `MediaOutlet` con la plataforma.

## Tabla resumen

| Rol | Decide sobre artículos | Decide sobre redes | Configura la plataforma |
|---|---|---|---|
| Editor Jefe | Sí (además define reglas) | Indirectamente (reglas) | Reglas editoriales, fuentes |
| Editor | Sí | No | No |
| Editor de Redes | No | Sí | Cuentas de redes |
| Periodista | Propone, no aprueba (salvo que también sea Editor) | No | No |
| Administrador | No | No | Credenciales, usuarios |

## Por qué se define esto ahora, sin autenticación todavía

Definir los roles a nivel funcional antes de implementar permisos evita
que la primera versión de autenticación (ver
[docs/product/SAAS_EVOLUTION.md](../product/SAAS_EVOLUTION.md), etapa
"True SaaS") tenga que inventar el modelo de roles sobre la marcha. Hoy,
con un solo cliente y un equipo pequeño, estos roles son una guía de
responsabilidad, no una restricción técnica — cualquier persona del
equipo de Portal Vallenato puede, en la práctica, hacer lo que el sistema
le permita hacer manualmente en Telegram y WordPress.

## Ver también

- [docs/product/DOMAIN_MODEL.md](../product/DOMAIN_MODEL.md) — la
  entidad `Editor` y sus relaciones.
- [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md) — por qué todos estos
  roles son humanos, no agentes de IA.
