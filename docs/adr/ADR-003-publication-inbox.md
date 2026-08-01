# ADR-003: Publication Inbox como frontera única de entrada multicanal

- **Estado:** Aceptado
- **Fecha:** 2026-07-30 (Sprint 3A — Product Repositioning & Architecture)
- **Contexto del documento:** ver [ADR-001](ADR-001-project-vision.md) para
  las convenciones de formato. Este ADR no reemplaza ni modifica ADR-001 ni
  ADR-002 — los extiende con las decisiones de modelado tomadas durante el
  reposicionamiento comercial de Sprint 3A, antes de que Sprint 3D empiece
  a implementar código sobre estos conceptos.

## Contexto

Hasta Sprint 2, el único punto de entrada de contenido al sistema era
`core.services.discovery_engine.DiscoveryEngine`, alimentado por fuentes
tipo RSS/sitio vía `core.ports.content_source.ContentSource`. El
reposicionamiento de Sprint 3A estableció que, para el cliente piloto
(Portal Vallenato), la mayoría de las publicaciones **no** se originan ahí:
llegan directamente por WhatsApp desde managers, artistas y empresas, con
texto, imágenes, videos y comunicados exclusivos — contenido generalmente
**comercial**, no descubierto.

Se necesita una entidad que unifique cualquier canal de entrada (WhatsApp,
Radar, entrada manual, y a futuro Email) en una forma única que el pipeline
editorial existente (Extractor → Writer → SEO → Images → WordPress →
Telegram → aprobación humana) pueda consumir sin conocer de dónde vino el
contenido.

## Decisión 1 — El bounded context se llama "Publication Inbox", no "Intake"

Se evaluaron tres nombres: "Intake" (genérico, técnico), "Content Inbox"
(ambiguo con el vocabulario que ya usan Discovery/Editorial para
"contenido") y **"Publication Inbox"**. Se elige este último porque:

- Liga directamente con el nombre de la entidad central,
  `PublicationRequest` — el nombre del bounded context y el de su entidad
  principal se leen como la misma idea, sin traducción mental.
- Es un término de negocio, no técnico: describe "la bandeja de entrada de
  solicitudes de publicación", algo que un editor o un responsable
  comercial entiende sin explicación, consistente con
  [docs/PROJECT_RULES.md](../PROJECT_RULES.md), regla 8 (nombres que
  reflejan el vocabulario del negocio).
- Evita colisión con "contenido", palabra que Discovery y Editorial ya usan
  con un significado propio (contenido extraído, cuerpo de un `Article`).

## Decisión 2 — `PublicationRequest` incluye contexto comercial desde el día uno

`NewsCandidate` (Sprint 2) **no se toca**: sigue siendo un concepto interno
de Discovery, con su propio significado (huella por URL, `confidence`,
"todavía no extraído"). No tiene sentido para un mensaje de WhatsApp que ya
trae contenido completo.

Se introduce `PublicationRequest` como entidad nueva, agnóstica de canal:

| Atributo | Responsabilidad |
|---|---|
| `origin` | De qué canal llegó (`RequestOrigin`: `WHATSAPP`, `RADAR`, `MANUAL`, `EMAIL`) |
| `is_commercial` | Si esta solicitud corresponde a contenido comercial — ver razonamiento abajo |
| `client_id` | Referencia por ID al `Client` de Commercial Manager, si ya se resolvió — ver [ADR-004](ADR-004-commercial-manager.md) |
| `campaign_id` | Referencia por ID a la `Campaign` a la que pertenece, si ya se resolvió |
| `commercial_contact_id` | Referencia por ID al `CommercialContact` que la envió, si aplica |
| `priority` | Urgencia operativa/comercial de la solicitud (distinta de `EditorialAssessment.priority`, que es una señal editorial sobre noticias orgánicas) |
| `requested_publish_at` | Fecha en la que el remitente pidió que se publique, si la especificó |
| `attachments` | Tupla de `MediaAsset` (imágenes, video, documentos) |
| `raw_text` | El texto tal como llegó, sin procesar |
| `requester_reference` | Identificador crudo del remitente en su canal (teléfono, id de fuente, ...) |
| `received_at` | Cuándo llegó |
| `status` | `PublicationRequestStatus`: `RECEIVED`, `IN_REVIEW`, `ACCEPTED`, `REJECTED`, `DUPLICATE` |

Se fija esta forma **ahora**, aunque `PublicationRequest` se implemente
recién en Sprint 3D (después de Commercial Manager Core, ver
[ADR-004](ADR-004-commercial-manager.md) y el roadmap actualizado), para no
requerir una migración de forma cuando Publication Inbox se conecte con
Commercial Manager.

### Por qué `is_commercial` es un campo independiente, no derivado de `origin`

`origin == WHATSAPP` no implica automáticamente contenido comercial: un
tipster o una fuente ciudadana podría enviar una noticia por WhatsApp sin
que exista ningún `Client` detrás. Del mismo modo, un canal no-WhatsApp
futuro podría, en teoría, traer contenido comercial. Mezclar ambos
conceptos en uno solo obligaría a inventar combinaciones de `origin`
artificiales (`WHATSAPP_COMMERCIAL`, `WHATSAPP_TIP`) cada vez que aparezca
un canal nuevo — el mismo problema que ADR-002 ya evitó al separar
`PublicationStatus` de `ArticleStatus`.

### Por qué `client_id`/`campaign_id`/`commercial_contact_id` son opcionales

Un `PublicationRequest` puede llegar por WhatsApp de un número no
reconocido, sin que todavía se sepa a qué `Client` o `CommercialContact`
corresponde. Esa resolución es un paso de **triage humano** (un editor o
responsable comercial la completa antes de aceptar la solicitud) — no un
requisito de captura. Forzar estos campos a ser obligatorios bloquearía la
recepción de contenido legítimo mientras se resuelve la identidad del
remitente.

## Decisión 3 — Radar se mapea a Publication Inbox sin modificar `DiscoveryEngine`

Un adaptador nuevo (`RadarPublicationInboxAdapter`, Sprint 3E) convierte
cada `NewsCandidate` producido por `DiscoveryEngine.run()` en un
`PublicationRequest` con `origin=RADAR`, `is_commercial=False`,
`client_id=None`. `DiscoveryEngine`, `generate_candidate_hash`,
`NewsCandidate`, `Source` y `ContentSource` quedan exactamente como están
— ver [docs/architecture/discovery-engine.md](../architecture/discovery-engine.md).

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Fusionar `NewsCandidate` y `PublicationRequest` en una sola entidad | Mismo argumento que ADR-002 para separar `EditorialAssessment`: ciclos de vida y forma de deduplicación distintos (huella por URL vs. sin URL) |
| Agregar los campos comerciales a `Article` en lugar de a `PublicationRequest` | `Article` debe seguir siendo agnóstico de canal y de cliente, igual que hoy — mezclar esto lo acoplaría a Commercial Manager |
| Derivar `is_commercial` de `origin == WHATSAPP` | No sostiene el caso de un tipster sin cliente comercial ni la posibilidad de canales comerciales futuros distintos de WhatsApp |

## Consecuencias

- `docs/product/DOMAIN_MODEL.md`, `docs/ARCHITECTURE.md`,
  `docs/architecture/system-overview.md`,
  `docs/architecture/publication-inbox.md` (nuevo),
  `docs/ROADMAP.md` y `docs/roadmap/v1-roadmap.md` se actualizan para
  reflejar esta decisión.
- Ningún código existente cambia — `NewsCandidate`, `Source`,
  `DiscoveryEngine`, `ContentSource` (Sprint 2) quedan exactamente como
  están.
- Queda pendiente de Sprint 3D: el puerto
  `core.ports.publication_inbox_channel.PublicationInboxChannel`
  (`Protocol`, análogo a `ContentSource`) y el evento
  `PublicationRequestReceived`.
- Ver [ADR-004](ADR-004-commercial-manager.md) para de dónde salen
  `client_id`, `campaign_id` y `commercial_contact_id`.
