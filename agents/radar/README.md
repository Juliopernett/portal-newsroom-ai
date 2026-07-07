# Radar Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 1.

## Responsabilidad

Vigilar continuamente las fuentes configuradas (sitios de noticias, feeds
RSS, etc.) y detectar contenido que sea nuevo, es decir, que no exista ya
en el historial editorial.

## Depende de

- `core.ports.content_source.ContentSource`
- `core.ports.repository.Repository` (para descartar duplicados contra el
  historial editorial)

## Produce

Una lista de referencias de contenido nuevo, que se entrega al agente
Extractor.
