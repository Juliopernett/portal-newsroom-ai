# Radar Agent

**Estado:** No implementado. Planeado para docs/ROADMAP.md Fase 1.

## Responsabilidad

Vigilar continuamente las fuentes configuradas (sitios de noticias, feeds
RSS, etc.) y detectar contenido que sea nuevo, es decir, que no exista ya
en el historial editorial.

El motor de esta detección (`core.services.discovery_engine.DiscoveryEngine`
— agregación, deduplicación por hash y ordenamiento de candidatos) ya
existe desde Sprint 2. Lo que falta para que este agente exista de verdad:
un `ContentSource` real por fuente (RSS, crawler, ...) y la integración
con `Repository` para descartar contra el historial editorial persistido
(el `DiscoveryEngine` solo deduplica dentro de una misma pasada).

## Depende de

- `core.services.discovery_engine.DiscoveryEngine`
- `core.ports.content_source.ContentSource` (uno o más adaptadores reales)
- `core.ports.repository.Repository` (para descartar duplicados contra el
  historial editorial)

## Produce

Un evento `NewsFound` con los candidatos nuevos, que se entrega al agente
Extractor.
