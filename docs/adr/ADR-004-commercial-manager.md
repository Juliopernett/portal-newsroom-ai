# ADR-004: Commercial Manager como bounded context independiente, Campaign como unidad operativa

- **Estado:** Aceptado
- **Fecha:** 2026-07-30 (Sprint 3A — Product Repositioning & Architecture)
- **Contexto del documento:** ver [ADR-001](ADR-001-project-vision.md) para
  las convenciones de formato. Extiende ADR-003, no lo reemplaza.

## Contexto

Portal Vallenato recibe la mayoría de su contenido publicable como
solicitudes comerciales — managers, artistas y empresas que pagan (o
tienen un acuerdo) por espacio editorial/promocional. Hoy esto se
administra fuera del sistema (WhatsApp + memoria del equipo). Se necesita
un bounded context que administre clientes, contratos, planes, campañas,
cuotas y alertas, sin acoplarse al dominio Editorial existente.

## Decisión 1 — `Client` no es `MediaOutlet`

`docs/product/DOMAIN_MODEL.md` ya define `MediaOutlet` (conceptual, no
implementada): el **tenant** de la plataforma — hoy hay exactamente uno,
Portal Vallenato. `Client` (Commercial Manager) es algo distinto: **un
cliente comercial de Portal Vallenato** — el manager, artista o empresa
que paga por publicar. Todo `Client` vive dentro del único `MediaOutlet`
implícito del MVP.

Esta distinción se documenta explícitamente porque ambos conceptos
"suenan" a multi-tenencia y son fáciles de confundir, especialmente cuando
`MediaOutlet` se implemente de verdad en v1.1 — ver
[docs/product/SAAS_EVOLUTION.md](../product/SAAS_EVOLUTION.md). Introducir
`Client` **no** es un paso hacia multi-tenencia ni contradice
[docs/product/MVP_SCOPE.md](../product/MVP_SCOPE.md): es un concepto de
negocio de un único cliente de la plataforma (Portal Vallenato), igual que
`Source` lo es hoy.

## Decisión 2 — `CommercialContact` se separa de `Client`

Quien físicamente envía contenido por WhatsApp (un manager, un asistente de
prensa) no es necesariamente el titular del acuerdo comercial. Se modela
`CommercialContact` como entidad propia:

| Atributo | Responsabilidad |
|---|---|
| `name` | Nombre de la persona |
| `phone` | Número de WhatsApp — la clave con la que Publication Inbox resuelve `commercial_contact_id` en un `PublicationRequest` entrante |
| `role` | Rol de quien contacta (manager, artista, encargado de prensa, otro) |
| `client_id` | El `Client` al que representa — **opcional** |
| `status` | Activo/inactivo |

`client_id` es opcional porque un contacto puede escribir antes de que
alguien del equipo lo vincule a un `Client` existente — la resolución
ocurre en el mismo paso de triage humano que ya describe
[ADR-003](ADR-003-publication-inbox.md). Un `Client` puede tener varios
`CommercialContact` (un artista y su manager, por ejemplo); en el MVP cada
`CommercialContact` representa a lo sumo un `Client` a la vez — si un
mismo contacto gestiona varios clientes, se resuelve caso a caso en
triage, no con una relación muchos-a-muchos en el modelo (evita
complejidad que ningún caso real ha justificado todavía).

## Decisión 3 — `Campaign` es la unidad operativa; `Contract` es el acuerdo comercial

Se le da a `Campaign` el protagonismo central que antes tenía implícitamente
`Contract`:

- **`Contract`** representa el acuerdo comercial/legal con un `Client`: a
  qué `Plan` está suscrito, vigencia, estado. Responde "¿qué se acordó y
  hasta cuándo es válido?".
- **`Campaign`** representa el trabajo que realmente se ejecuta: una serie
  de `PublicationRequest`/`Article` con un objetivo concreto (ej. "lanzamiento
  de disco X", "cobertura de evento Y"). Responde "¿qué se está haciendo
  ahora mismo para este cliente?".

`PublicationRequest` (ADR-003) y `PublicationRegistryEntry` (ver Decisión 5)
se atan primariamente a `Campaign`, no directamente a `Contract`. Una
`Campaign` puede existir **sin** `Contract` asociado (`contract_id: str |
None`) — una campaña de cortesía, una prueba, o trabajo comercial iniciado
antes de formalizar papeles es un estado de negocio válido, no un error de
datos. En ese caso, simplemente no hay cuota que vigilar para esa campaña.

| Entidad | Atributos clave |
|---|---|
| `Contract` | `id`, `client_id`, `plan_id`, `start_date`, `end_date`, `status` |
| `Plan` | `id`, `name`, `monthly_quota`, `price`, `channels_included` |
| `Campaign` | `id`, `client_id`, `contract_id` (opcional), `name`, `objective`, `start_date`, `end_date`, `status`, `priority` |

### Por qué no se fusionan `Campaign` y `Contract`

Un mismo `Contract` puede cubrir varias campañas a lo largo de su vigencia
(un cliente con un plan mensual que lanza tres campañas distintas ese mes).
Fusionarlos obligaría a un contrato nuevo por cada iniciativa operativa,
mezclando lo legal/comercial con lo operativo — el mismo tipo de problema
que ADR-002 evitó al separar `Article` de `Publication`.

## Decisión 4 — La cuota se deriva, nunca se cuenta con un campo mutable

No existe `Quota.used` como campo que se incrementa. Se calcula contando
`PublicationRegistryEntry` por `campaign_id`/`contract_id` y periodo. Mismo
argumento que ADR-002 usa para `EditorialAssessment`: un contador mutable
es una fuente de bugs de concurrencia y pierde auditabilidad; un conteo
derivado de hechos inmutables no.

## Decisión 5 — Integración con Editorial: solo por ID, nunca por import directo

`Commercial Manager` no importa entidades de Editorial ni viceversa. El
único puente es:

1. **En la entrada:** `PublicationRequest.client_id` /
   `campaign_id` / `commercial_contact_id` (ADR-003) — referencias por
   `str`, resueltas por el canal WhatsApp o por triage humano.
2. **En la salida:** cuando un `Article` de origen comercial llega a
   `ArticleStatus.PUBLISHED`, un `workflow` (nunca `core/` directamente)
   registra un `PublicationRegistryEntry` con `campaign_id` y `article_id`.
   No se depende de la entidad `Publication` (ADR-002, todavía conceptual)
   para esto — `ArticleStatus.PUBLISHED` es suficiente señal para el MVP;
   si `Publication` se implementa más adelante, `PublicationRegistryEntry`
   puede empezar a referenciar también `publication_id` sin romper nada
   (cambio aditivo).

Esto es el mismo patrón que ya usa el proyecto para WordPress/Telegram: sin
event bus (ver [docs/ARCHITECTURE.md](../ARCHITECTURE.md), sección
"Eventos de dominio"), `workflows/` es el mecanismo de coordinación entre
bounded contexts, nunca un import cruzado entre sus `core/entities/`.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Fusionar `Client` y `MediaOutlet` | Son conceptos distintos: tenant de la plataforma vs. cliente comercial de un tenant — fusionarlos bloquearía v1.1 (`MediaOutlet` real) sin ninguna ganancia |
| `PublicationRegistryEntry` referenciando `contract_id` directamente | Pierde trazabilidad operativa — no se sabría a qué campaña concreta corresponde una publicación, solo a qué acuerdo comercial |
| Contador mutable de cuota en `Contract` o `Plan` | Riesgo de doble conteo/pérdida de auditoría — ver Decisión 4 |
| `Commercial Manager` viviendo dentro de `agents/` como un agente más | No encaja en la metáfora de "agente" (automatización de una tarea mecánica del pipeline) — es un contexto de gestión con sus propias entidades y reglas de negocio, más parecido a Editorial que a un agente individual |

## Consecuencias

- El roadmap se reordena: Commercial Manager Core y su Dashboard se
  construyen **antes** que las integraciones de canal (Radar, WhatsApp) —
  ver `docs/ROADMAP.md` y `docs/roadmap/v1-roadmap.md` actualizados.
- `docs/product/MVP_SCOPE.md` se actualiza: `Client`, `CommercialContact`,
  `Contract`, `Plan`, `Campaign` pasan a estar **dentro** del MVP de
  Portal Vallenato (no son multi-tenencia, ver Decisión 1).
- Ningún código existente cambia.
- Queda pendiente de Sprint 3B: `core.ports.repository.Repository[T]`
  genérico (ya existe, sin cambios) reutilizado para cada entidad nueva vía
  sus propios repositorios concretos en `database/repositories/`.
