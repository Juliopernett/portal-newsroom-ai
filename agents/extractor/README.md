# Extractor Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 1.

## Responsabilidad

A partir de una referencia de contenido (típicamente una URL) detectada por
Radar, extraer el contenido completo de forma estructurada: título, cuerpo,
imágenes y metadatos, usando Playwright, BeautifulSoup y/o Requests.

## Depende de

- `core.ports.content_extractor.ContentExtractor`

## Produce

Contenido estructurado, que se entrega al agente Writer.
