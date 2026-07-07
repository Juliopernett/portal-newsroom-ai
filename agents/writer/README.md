# Writer Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 2.

## Responsabilidad

Reescribir el contenido extraído con el estilo editorial de Portal
Vallenato, usando un proveedor de IA. Las plantillas de prompt usadas para
esta reescritura vivirán en `prompts/`.

## Depende de

- `core.ports.ai_provider.AIProvider`

## Produce

El artículo reescrito, que se entrega al agente SEO.
