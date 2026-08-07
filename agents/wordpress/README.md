# WordPress Agent

**Estado:** `client.py` implementa `CMSPublisher` contra la REST API real
de WordPress (Sprint 4A, Incremento 3 — ver
[ADR-006](../../docs/adr/ADR-006-multichannel-publication.md)), para el
pilar comercial (`DestinoPublicacion`, canal `WORDPRESS`). El agente
completo para el pilar editorial (metadatos SEO, imágenes, entrega a
Telegram) sigue sin implementar — planeado para docs/ROADMAP.md Fase 3.

## Responsabilidad

Crear un **borrador** en WordPress vía su REST API. **Nunca publica** —
ver docs/PROJECT_RULES.md, regla 1: `client.py` siempre envía
`status=draft`, sin excepción.

## Depende de

- `core.ports.cms_publisher.CMSPublisher`
- Application Password de WordPress (`WORDPRESS_SITE_URL`,
  `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` en `.env`) — nunca la
  contraseña de inicio de sesión real de la cuenta.

## Produce

`CMSDraftResult` (`post_id` + `url`) del borrador creado. En el pilar
comercial, `core.services.wordpress_publication_service.crear_borrador`
los adjunta a un `DestinoPublicacion`. En el pilar editorial (futuro),
se entregarían al agente Telegram para notificar al equipo.
