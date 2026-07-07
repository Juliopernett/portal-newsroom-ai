# WordPress Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 3.

## Responsabilidad

Crear un **borrador** en WordPress vía su REST API con el artículo,
metadatos SEO e imágenes ya preparados. **Nunca publica** — ver
docs/PROJECT_RULES.md, regla 1.

## Depende de

- `core.ports.cms_publisher.CMSPublisher`

## Produce

El identificador/URL del borrador creado, que se entrega al agente
Telegram para notificar al equipo editorial.
