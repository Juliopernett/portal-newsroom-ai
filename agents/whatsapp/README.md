# WhatsApp Agent

**Estado:** No implementado. Diseñado en Sprint 3A, planeado para
docs/ROADMAP.md Fase 1.5 (Sprint 3F).

## Responsabilidad

Recibir solicitudes de publicación enviadas por WhatsApp — managers,
artistas y empresas que envían texto, imágenes, videos y comunicados,
generalmente con interés comercial. Es uno de varios canales de
**Publication Inbox** (ver
[docs/architecture/publication-inbox.md](../../docs/architecture/publication-inbox.md)),
no un agente del pipeline editorial en sí.

Cuando el número remitente coincide con un `CommercialContact` conocido,
resuelve `client_id`/`commercial_contact_id` automáticamente; si no,
entrega el `PublicationRequest` sin vincular para que un responsable
comercial lo resuelva en triage — ver
[docs/business/commercial-workflow.md](../../docs/business/commercial-workflow.md).

## Depende de

- `core.ports.publication_inbox_channel.PublicationInboxChannel` (planeado,
  Sprint 3D)
- Commercial Manager (`Client`, `CommercialContact`) para la resolución de
  identidad — solo por referencia de ID, nunca por import directo — ver
  [ADR-004](../../docs/adr/ADR-004-commercial-manager.md), Decisión 5.

## Produce

`PublicationRequest` con `origin=WHATSAPP` — ver
[ADR-003](../../docs/adr/ADR-003-publication-inbox.md).

## Nota de riesgo técnico

La integración con WhatsApp Business API (verificación de Meta Business,
plantillas para mensajes salientes, expiración de URLs de medios) es un
riesgo operativo independiente del diseño de dominio — merece su propio
spike antes de empezar Sprint 3F.
